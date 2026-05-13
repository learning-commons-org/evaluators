"""Tests for SDK logging helpers."""

import logging
from io import StringIO

from learning_commons_evaluators.logger import (
    SDK_LOGGER_NAME,
    create_logger,
    create_silent_logger,
    format_error,
    get_logger,
)


class TestGetLogger:
    def test_root_name(self) -> None:
        log = get_logger()
        assert log.name == SDK_LOGGER_NAME

    def test_child_name(self) -> None:
        log = get_logger("evaluators")
        assert log.name == f"{SDK_LOGGER_NAME}.evaluators"


class TestCreateLogger:
    def test_returns_use_logger_unchanged(self) -> None:
        custom = logging.getLogger("my_app.tests")
        result = create_logger(use_logger=custom)
        assert result is custom

    def test_default_adds_stream_handler(self) -> None:
        child = get_logger("test_create_default")
        # Isolate from other tests: fresh child name
        for h in list(child.handlers):
            child.removeHandler(h)
        log = create_logger("test_create_default", level=logging.INFO)
        assert isinstance(log.handlers[-1], logging.StreamHandler)
        log.setLevel(logging.INFO)

    def test_stream_handler_emits(self, capsys) -> None:
        buf = StringIO()
        h = logging.StreamHandler(buf)
        h.setFormatter(logging.Formatter("%(message)s"))
        log = create_logger("test_emit", level=logging.DEBUG, handler=h)
        log.info("hello")
        assert "hello" in buf.getvalue()

    def test_respects_level_on_stream_handler(self) -> None:
        buf = StringIO()
        h = logging.StreamHandler(buf)
        h.setLevel(logging.ERROR)
        log = create_logger("test_level", level=logging.DEBUG, handler=h)
        log.setLevel(logging.DEBUG)
        log.info("nope")
        log.error("yep")
        out = buf.getvalue()
        assert "nope" not in out
        assert "yep" in out


class TestCreateSilentLogger:
    def test_no_output(self, capsys) -> None:
        log = create_silent_logger()
        log.critical("should not appear")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    def test_clears_pre_existing_handlers(self, capsys) -> None:
        log = logging.getLogger("learning_commons_evaluators.silent")
        for h in list(log.handlers):
            log.removeHandler(h)
        noisy = logging.StreamHandler()
        log.addHandler(noisy)
        log.setLevel(logging.DEBUG)
        silent = create_silent_logger()
        assert silent is log
        silent.info("still silent")
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""
        for h in log.handlers:
            assert isinstance(h, logging.NullHandler)


class TestFormatError:
    def test_format_error_returns_string(self) -> None:
        err = ValueError("bad value")
        s = format_error(err)
        assert "ValueError" in s
        assert "bad value" in s
