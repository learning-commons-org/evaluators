"""An event's source information: which SDK sent it, and which client it belongs to.

The client id is shared state on disk with the TypeScript SDK — same file, same key — so
these checks are about interoperating with a file this SDK did not necessarily write, and
about never letting a filesystem that cannot be written stop an evaluation.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest

from learning_commons_evaluators import __version__
from learning_commons_evaluators.telemetry import utils

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")


@pytest.fixture(autouse=True)
def home(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """A home directory of this test's own, and no id carried over from another."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(utils, "_client_id", None)
    monkeypatch.delenv("APPDATA", raising=False)
    return tmp_path


def config_path(home: Path) -> Path:
    return home / ".config" / "learning-commons" / "config.json"


class TestSdkVersion:
    def test_names_this_sdk_and_its_version(self) -> None:
        assert utils.sdk_version() == f"learning-commons-evaluators-python-{__version__}"

    def test_is_the_identifier_the_typescript_sdk_does_not_use(self) -> None:
        # The field is shared, so the value is what tells the collector which SDK sent the
        # event: TypeScript sends a bare version there.
        assert utils.sdk_version().startswith("learning-commons-evaluators-python-")
        assert re.search(r"\d+\.\d+\.\d+", utils.sdk_version())


class TestTimestamp:
    def test_is_millisecond_utc_in_the_shape_javascript_writes(self) -> None:
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", utils.utc_timestamp())

    def test_writes_the_exact_string_javascript_would_for_a_known_instant(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # The shape check above passes for any plausible clock. Freezing it pins the two
        # things that could actually drift: that microseconds are truncated to
        # milliseconds rather than rounded, and that the offset is rendered as ``Z``.
        frozen = datetime(2026, 9, 17, 18, 4, 5, 123_789, tzinfo=timezone.utc)

        class _Frozen(datetime):
            @classmethod
            def now(cls, tz=None):  # type: ignore[override]
                return frozen if tz is None else frozen.astimezone(tz)

        monkeypatch.setattr(utils, "datetime", _Frozen)

        # 123_789 microseconds is 123.789 ms — truncated, not rounded to 124.
        assert utils.utc_timestamp() == "2026-09-17T18:04:05.123Z"


class TestClientId:
    def test_generates_and_saves_an_id_when_there_is_no_config_file(self, home: Path) -> None:
        generated = utils.client_id()

        assert UUID.match(generated)
        saved = json.loads(config_path(home).read_text(encoding="utf-8"))
        assert saved == {"telemetry": {"clientId": generated}}

    def test_reads_the_id_the_typescript_sdk_saved(self, home: Path) -> None:
        existing = "a1b2c3d4-e5f6-4789-ab01-cd23ef456789"
        path = config_path(home)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"telemetry": {"clientId": existing}}), encoding="utf-8")

        assert utils.client_id() == existing

    def test_reads_from_disk_once_per_process(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        reads: list[Path] = []
        original = utils._read_config

        def record(path: Path) -> dict[str, object]:
            reads.append(path)
            return original(path)

        monkeypatch.setattr(utils, "_read_config", record)

        assert utils.client_id() == utils.client_id()
        assert len(reads) == 1

    def test_keeps_what_else_the_shared_file_holds(self, home: Path) -> None:
        # The file belongs to both SDKs and to whatever comes next; a key this SDK does not
        # know about is not ours to drop.
        path = config_path(home)
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({"other": {"kept": True}, "telemetry": {}}), encoding="utf-8")

        generated = utils.client_id()

        saved = json.loads(path.read_text(encoding="utf-8"))
        assert saved == {"other": {"kept": True}, "telemetry": {"clientId": generated}}

    @pytest.mark.parametrize(
        "contents",
        ["not json at all", "[]", '{"telemetry": {"clientId": ""}}'],
        ids=["malformed", "not-an-object", "empty-id"],
    )
    def test_generates_an_id_when_the_file_cannot_be_used(self, home: Path, contents: str) -> None:
        path = config_path(home)
        path.parent.mkdir(parents=True)
        path.write_text(contents, encoding="utf-8")

        assert UUID.match(utils.client_id())

    def test_a_filesystem_it_cannot_write_still_yields_an_id(
        self, home: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # A read-only container or serverless sandbox: the id is then per-process, and
        # telemetry is anonymous either way.
        def read_only(*args: object, **kwargs: object) -> None:
            raise OSError("EROFS")

        monkeypatch.setattr(Path, "mkdir", read_only)

        assert UUID.match(utils.client_id())
        assert not config_path(home).exists()


class TestWhereTheConfigLives:
    def test_follows_xdg_on_posix(self, home: Path) -> None:
        assert utils.config_file() == config_path(home)

    def test_follows_appdata_on_windows(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ) -> None:
        # A stub rather than the real module: setting ``os.name`` for real would have
        # ``Path`` hand back a ``WindowsPath`` this machine cannot instantiate.
        appdata = tmp_path / "AppData"
        monkeypatch.setattr(
            utils, "os", SimpleNamespace(name="nt", environ={"APPDATA": str(appdata)})
        )

        assert utils.config_file() == appdata / "learning-commons" / "config.json"

    def test_falls_back_to_the_home_directory_when_windows_has_no_appdata(
        self, monkeypatch: pytest.MonkeyPatch, home: Path
    ) -> None:
        monkeypatch.setattr(utils, "os", SimpleNamespace(name="nt", environ={}))

        assert utils.config_file() == home / "learning-commons" / "config.json"


class TestUtf16Length:
    """``text_length_chars`` must mean the same count in both SDKs' events.

    Python's ``len`` counts code points; JavaScript's ``String.length`` counts UTF-16 code
    units. The TypeScript event is the oracle, so the Python count follows it.
    """

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("", 0),
            ("plain ascii", 11),
            ("caf\u00e9", 4),  # BMP: one unit per character, same as len()
            ("\U0001f389", 2),  # non-BMP: one code point, two UTF-16 code units
            ("great job \U0001f389\U0001f331", 14),  # len() would say 12
        ],
    )
    def test_counts_utf16_code_units(self, text: str, expected: int) -> None:
        assert utils.utf16_length(text) == expected

    def test_differs_from_len_only_outside_the_bmp(self) -> None:
        ascii_text = "The cat sat on the mat."
        assert utils.utf16_length(ascii_text) == len(ascii_text)
        emoji = "done \U0001f389"
        assert utils.utf16_length(emoji) == len(emoji) + 1
