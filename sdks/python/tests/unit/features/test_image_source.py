"""Reading an attached image and holding it to the contract's ``x-image`` bounds.

The images are real files encoded by Pillow, so what is accepted here is what a vendor can
decode; only the forgeries and the oversized header are written byte by byte, since no
encoder would produce them.
"""

from __future__ import annotations

import io
import json
import os
import struct
import sys
import zlib
from dataclasses import replace
from pathlib import Path

import pytest
from PIL import Image

from learning_commons_evaluators import InputValidationError
from learning_commons_evaluators.features.image_source import (
    ImageBounds,
    ImageInfo,
    inspect_image,
    load_image,
)

CONTRACT_DIR = Path(__file__).resolve().parents[5] / "evals/graphics/math/graphics-accuracy"
FIXTURE_IMAGE = CONTRACT_DIR / "images/apples-in-baskets.png"

#: The bounds a real contract declares, so these tests exercise the numbers that ship.
_DECLARED = json.loads((CONTRACT_DIR / "input_schema.json").read_text(encoding="utf-8"))[
    "properties"
]["image_paths"]["items"]["x-image"]
BOUNDS = ImageBounds(
    formats=tuple(_DECLARED["formats"]),
    detect=_DECLARED["detect"],
    min_bytes=_DECLARED["min_bytes"],
    max_bytes=_DECLARED["max_bytes"],
    min_edge=_DECLARED["min_edge"],
    max_edge=_DECLARED["max_edge"],
)


def encoded(fmt: str, width: int, height: int, **options: object) -> bytes:
    """A real image of ``width``×``height`` in Pillow's ``fmt``."""
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 30, 30)).save(buffer, fmt, **options)
    return buffer.getvalue()


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))


def png_declaring(width: int, height: int) -> bytes:
    """A well-formed PNG whose header declares ``width``×``height`` over a few bytes of data."""
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(b"\0" * 64))
        + _chunk(b"IEND", b"")
    )


def padded(head: bytes, size: int = 100) -> bytes:
    return head + bytes(size - len(head))


class TestInspectImage:
    def test_reads_the_format_and_dimensions_of_png_jpeg_and_webp(self) -> None:
        assert inspect_image(encoded("PNG", 640, 480)) == ImageInfo("image/png", 640, 480)
        assert inspect_image(encoded("JPEG", 1024, 768)) == ImageInfo("image/jpeg", 1024, 768)
        assert inspect_image(encoded("WEBP", 2560, 16)) == ImageInfo("image/webp", 2560, 16)
        assert inspect_image(encoded("WEBP", 300, 200, lossless=True)) == ImageInfo(
            "image/webp", 300, 200
        )

    def test_reads_a_multi_picture_jpeg_as_jpeg(self) -> None:
        # Pillow names a JPEG with extra frames MPO; its bytes are a JPEG stream all the same.
        frames = [Image.new("RGB", (512, 256), colour) for colour in ("red", "blue")]
        buffer = io.BytesIO()
        frames[0].save(buffer, "MPO", save_all=True, append_images=frames[1:])
        assert inspect_image(buffer.getvalue()) == ImageInfo("image/jpeg", 512, 256)

    def test_reads_a_real_fixture_image(self) -> None:
        image = inspect_image(FIXTURE_IMAGE.read_bytes())
        assert image is not None
        assert image.media_type == "image/png"
        assert image.width > 0 and image.height > 0

    def test_rejects_anything_else(self) -> None:
        # A GIF is an image Pillow reads, but not one this SDK is told to try.
        assert inspect_image(encoded("GIF", 50, 50)) is None
        # A forged PNG prefix, a JPEG that ends before any frame, and plain non-images.
        assert inspect_image(padded(b"\x89PNG\0\0\0\0")) is None
        assert inspect_image(padded(b"\xff\xd8\xff\xd9")) is None
        assert inspect_image(b"not an image") is None
        assert inspect_image(b"") is None

    def test_rejects_a_header_that_is_not_followed_by_a_well_formed_image(self) -> None:
        # Stricter than a header sniffer, deliberately: bytes a decoder cannot walk are bytes
        # a model cannot read either.
        whole = encoded("PNG", 640, 480)
        assert inspect_image(padded(whole[:33], 200)) is None


class TestLoadImage:
    def write(self, tmp_path: Path, name: str, data: bytes) -> str:
        path = tmp_path / name
        path.write_bytes(data)
        return str(path)

    def test_returns_the_exact_bytes_with_the_detected_media_type(self, tmp_path: Path) -> None:
        data = encoded("PNG", 512, 256)
        # The extension is deliberately meaningless: the bytes decide.
        attachment = load_image("image_paths[0]", self.write(tmp_path, "chart.dat", data), BOUNDS)
        assert attachment.data == data
        assert attachment.media_type == "image/png"

    def test_accepts_a_real_fixture_image_within_the_shipped_bounds(self) -> None:
        attachment = load_image("image_paths[0]", str(FIXTURE_IMAGE), BOUNDS)
        assert attachment.media_type == "image/png"
        assert attachment.data == FIXTURE_IMAGE.read_bytes()

    def test_accepts_a_path_relative_to_the_working_directory(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        self.write(tmp_path, "here.png", encoded("PNG", 100, 100))
        monkeypatch.chdir(tmp_path)
        assert load_image("f", "here.png", BOUNDS).media_type == "image/png"

    def test_names_the_field_and_position_in_every_error(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError, match=r"^image_paths\[2\]: could not read file"):
            load_image("image_paths[2]", str(tmp_path / "missing.png"), BOUNDS)

    def test_an_unreadable_path_keeps_its_cause(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError) as caught:
            load_image("f", str(tmp_path / "missing.png"), BOUNDS)
        assert isinstance(caught.value.__cause__, FileNotFoundError)

    def test_a_path_the_os_cannot_take_is_unreadable_not_a_crash(self) -> None:
        with pytest.raises(InputValidationError, match="could not read file"):
            load_image("f", "bad\0path.png", BOUNDS)

    def test_rejects_a_file_that_is_not_an_accepted_image_by_its_bytes(
        self, tmp_path: Path
    ) -> None:
        path = self.write(tmp_path, "note.png", padded(b"not an image"))
        with pytest.raises(
            InputValidationError, match=r"not an accepted image \(PNG, JPEG, WEBP\)"
        ):
            load_image("f", path, BOUNDS)

    def test_rejects_a_format_the_contract_does_not_list(self, tmp_path: Path) -> None:
        png_only = replace(BOUNDS, formats=("image/png",))
        path = self.write(tmp_path, "photo.jpg", encoded("JPEG", 100, 100))
        with pytest.raises(InputValidationError, match=r"\(PNG\)"):
            load_image("f", path, png_only)

    def test_rejects_a_file_below_min_bytes_including_an_empty_one(self, tmp_path: Path) -> None:
        with pytest.raises(
            InputValidationError, match=r"0 bytes \(0\.00 MB\); the minimum is 64 bytes"
        ):
            load_image("f", self.write(tmp_path, "empty.png", b""), BOUNDS)
        with pytest.raises(InputValidationError, match="minimum is 64"):
            load_image("f", self.write(tmp_path, "tiny.png", encoded("PNG", 20, 20)[:40]), BOUNDS)

    def test_rejects_a_file_over_max_bytes_by_its_size_on_disk(self, tmp_path: Path) -> None:
        big = padded(encoded("PNG", 100, 100), BOUNDS.max_bytes + 1)
        with pytest.raises(
            InputValidationError,
            match=r"5,242,881 bytes \(5\.00 MB\); the maximum is 5,242,880 bytes",
        ):
            load_image("f", self.write(tmp_path, "huge.png", big), BOUNDS)

    def test_reads_no_more_than_one_byte_past_max_bytes(self, tmp_path: Path) -> None:
        # The size on disk is checked first, but the read is capped too, so a file that grows
        # between the check and the read is still caught by the length of what was read.
        small = replace(BOUNDS, max_bytes=200)
        path = self.write(tmp_path, "grown.png", padded(encoded("PNG", 20, 20), 5000))
        real_fstat = os.fstat

        class Shrunk:
            """The file's real stat, except that it reports the size it had before growing."""

            def __init__(self, result: os.stat_result) -> None:
                self._result = result
                self.st_size = 10

            def __getattr__(self, name: str) -> object:
                return getattr(self._result, name)

        def lying_fstat(fd: int) -> object:
            return Shrunk(real_fstat(fd))

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(os, "fstat", lying_fstat)
            with pytest.raises(InputValidationError, match=r"201 bytes .* the maximum is 200"):
                load_image("f", path, small)

    def test_rejects_an_edge_below_min_edge(self, tmp_path: Path) -> None:
        path = self.write(tmp_path, "narrow.png", encoded("PNG", 10, 400))
        with pytest.raises(InputValidationError, match="10×400 px; each edge must be 16 to 2560"):
            load_image("f", path, BOUNDS)

    def test_rejects_an_edge_above_max_edge_and_says_how_to_fix_it(self, tmp_path: Path) -> None:
        path = self.write(tmp_path, "wide.webp", encoded("WEBP", 2677, 1605))
        with pytest.raises(
            InputValidationError, match="2677×1605 px.*Resize to 2560 px on the long edge"
        ):
            load_image("f", path, BOUNDS)

    def test_accepts_both_edges_exactly_at_the_bounds(self, tmp_path: Path) -> None:
        path = self.write(tmp_path, "edge.png", encoded("PNG", 2560, 16))
        assert load_image("f", path, BOUNDS).media_type == "image/png"

    def test_a_header_too_large_to_open_is_an_edge_failure(self, tmp_path: Path) -> None:
        # Pillow will not open a header declaring this many pixels, so the dimensions are never
        # read; the caller still learns what to do about it.
        path = self.write(tmp_path, "bomb.png", png_declaring(20000, 20000))
        with pytest.raises(
            InputValidationError,
            match="more pixels than can be read safely.*Resize to 2560 px",
        ):
            load_image("f", path, BOUNDS)

    def test_rejects_a_path_that_is_not_a_regular_file(self, tmp_path: Path) -> None:
        with pytest.raises(InputValidationError, match="is not a regular file"):
            load_image("f", str(tmp_path), BOUNDS)

    @pytest.mark.skipif(sys.platform == "win32", reason="no FIFOs on Windows")
    def test_refuses_a_fifo_without_blocking_on_it(self, tmp_path: Path) -> None:
        fifo = tmp_path / "pipe.png"
        os.mkfifo(fifo)
        # With a blocking open this would hang until a writer appeared.
        with pytest.raises(InputValidationError, match="is not a regular file"):
            load_image("f", str(fifo), BOUNDS)

    def test_rejects_a_header_it_cannot_read(self, tmp_path: Path) -> None:
        path = self.write(tmp_path, "bad.jpg", padded(b"\xff\xd8\xff\xd9"))
        with pytest.raises(InputValidationError, match="not an accepted image"):
            load_image("f", path, BOUNDS)


def test_the_loader_knows_every_format_the_providers_accept() -> None:
    # TypeScript makes this a compile error; here it is a test. A format added to
    # ``ImageMediaType`` that Pillow is not told to read would be refused as "not an image".
    from typing import get_args

    from learning_commons_evaluators.features.image_source import _MEDIA_TYPES
    from learning_commons_evaluators.providers import ImageMediaType

    assert set(_MEDIA_TYPES.values()) == set(get_args(ImageMediaType))
