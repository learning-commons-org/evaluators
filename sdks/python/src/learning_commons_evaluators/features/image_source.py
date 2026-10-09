"""Loading an image input for a vision evaluator.

A contract declares an attached input as an array of local file paths, and bounds each file
with an ``x-image`` block on the array's items. Each path is read here, in the caller's
environment, and its bytes leave only as part of the model request. Format and dimensions
are taken from the file's own bytes, never from its name, so a mislabelled or oversized
file is caught before a paid call.

The SDK is therefore reading files the caller names. That is the intended posture — the
caller's own environment, the caller's own images — and callers relaying paths from
untrusted parties should resolve them to files they control first.
"""

from __future__ import annotations

import io
import os
import stat
from dataclasses import dataclass
from typing import Literal, NamedTuple

from learning_commons_evaluators.errors import InputValidationError
from learning_commons_evaluators.providers.base import (
    AttachmentPosition,
    ImageAttachment,
    ImageMediaType,
)


@dataclass(frozen=True)
class ImageBounds:
    """The per-file bounds a contract declares in ``x-image``, as the SDK reads them."""

    formats: tuple[ImageMediaType, ...]
    detect: Literal["signature"]
    min_bytes: int
    max_bytes: int
    min_edge: int
    max_edge: int


class ImageInfo(NamedTuple):
    """What :func:`inspect_image` reads from an image's header."""

    media_type: ImageMediaType
    width: int
    height: int


#: Pillow's format names for the formats every supported vendor accepts. Pillow is told to
#: try only these, so no other decoder ever sees the caller's bytes.
_MEDIA_TYPES: dict[str, ImageMediaType] = {
    "PNG": "image/png",
    "JPEG": "image/jpeg",
    "WEBP": "image/webp",
}

#: The format names Pillow reports for an image opened by one of those readers. A JPEG
#: carrying extra frames (MPO, as many cameras write) is still a JPEG stream, but Pillow's
#: JPEG reader names it MPO; the TypeScript SDK reads it as JPEG too. MPO is not a reader of
#: its own, so it stays out of the list Pillow is told to try.
_REPORTED: dict[str, ImageMediaType] = {**_MEDIA_TYPES, "MPO": "image/jpeg"}


def inspect_image(data: bytes) -> ImageInfo | None:
    """Format and dimensions read from the image's own bytes — its signature and header,
    without decoding pixels — or ``None`` when the bytes are not a PNG, JPEG or WebP with a
    readable header, whatever the file is named.

    :raises PIL.Image.DecompressionBombError: when the header declares more pixels than
        Pillow will open, which is far beyond any edge bound a contract declares.
    """
    from PIL import Image

    try:
        with Image.open(io.BytesIO(data), formats=list(_MEDIA_TYPES)) as image:
            media_type = _REPORTED.get(image.format or "")
            width, height = image.size
    except Image.DecompressionBombError:
        raise
    except Exception:  # noqa: BLE001 — every way a header fails to parse means "not an image"
        return None
    if media_type is None or width <= 0 or height <= 0:
        return None
    return ImageInfo(media_type, width, height)


def _size(count: int) -> str:
    """Exact bytes, with MB alongside for readability: a file one byte over must not read as equal."""
    return f"{count:,} bytes ({count / (1024 * 1024):.2f} MB)"


def _read_bounded(path: str, field: str, max_bytes: int) -> bytes:
    """The file's bytes, refusing anything that is not a regular file within ``max_bytes``.

    One descriptor serves the check and the read, so the file cannot be swapped between
    them. ``O_NONBLOCK`` keeps a FIFO from blocking the open; it is then refused as not a
    regular file. At most ``max_bytes + 1`` bytes are read, so a file that grew after the
    check is cut off rather than read whole and the caller's size check rejects it.
    """
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    try:
        descriptor = os.open(path, flags)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode):
                raise InputValidationError(f'{field}: "{path}" is not a regular file.')
            if info.st_size > max_bytes:
                raise InputValidationError(
                    f'{field}: "{path}" is {_size(info.st_size)}; the maximum is {_size(max_bytes)}.'
                )
            chunks: list[bytes] = []
            remaining = max_bytes + 1
            while remaining > 0:
                chunk = os.read(descriptor, remaining)
                if not chunk:
                    break
                chunks.append(chunk)
                remaining -= len(chunk)
            return b"".join(chunks)
        finally:
            os.close(descriptor)
    except InputValidationError:
        raise
    except (OSError, ValueError) as cause:
        # ValueError covers a path the OS cannot take at all, such as one with a NUL byte.
        raise InputValidationError(f'{field}: could not read file "{path}".', cause) from cause


def load_image(
    field: str,
    path: str,
    bounds: ImageBounds,
    *,
    position: AttachmentPosition = "before_text",
) -> ImageAttachment:
    """Read the image at ``path`` and return it as an attachment, enforcing every bound the
    contract declares for it.

    Blocking file I/O; an evaluator runs it off the event loop.

    :param field: the input's name and position, for error messages (e.g. ``image_paths[0]``)
    :param path: a local file path, absolute or relative to the working directory
    :param bounds: the contract's ``x-image`` block for this input
    :param position: where the image goes relative to the user turn's text, as the contract's
        attachment declares it
    :raises InputValidationError: if the file cannot be read, is not an accepted format with
        a readable header by its bytes, or falls outside the declared size or edge bounds
    """
    data = _read_bounded(path, field, bounds.max_bytes)

    if len(data) < bounds.min_bytes:
        raise InputValidationError(
            f'{field}: "{path}" is {_size(len(data))}; the minimum is {_size(bounds.min_bytes)}.'
        )
    if len(data) > bounds.max_bytes:
        raise InputValidationError(
            f'{field}: "{path}" is {_size(len(data))}; the maximum is {_size(bounds.max_bytes)}.'
        )

    resize = f"Resize to {bounds.max_edge} px on the long edge before submitting."
    from PIL import Image

    try:
        image = inspect_image(data)
    except Image.DecompressionBombError as cause:
        raise InputValidationError(
            f'{field}: "{path}" declares more pixels than can be read safely; each edge must '
            f"be {bounds.min_edge} to {bounds.max_edge} px. {resize}",
            cause,
        ) from cause
    if image is None or image.media_type not in bounds.formats:
        accepted = ", ".join(f.removeprefix("image/").upper() for f in bounds.formats)
        raise InputValidationError(
            f'{field}: "{path}" is not an accepted image ({accepted}), judged by its bytes, '
            "not its name."
        )
    media_type, width, height = image
    if min(width, height) < bounds.min_edge or max(width, height) > bounds.max_edge:
        raise InputValidationError(
            f'{field}: "{path}" is {width}×{height} px; each edge must be {bounds.min_edge} '
            f"to {bounds.max_edge} px. {resize}"
        )

    return ImageAttachment(data=data, media_type=media_type, position=position)


__all__ = ["ImageBounds", "ImageInfo", "inspect_image", "load_image"]
