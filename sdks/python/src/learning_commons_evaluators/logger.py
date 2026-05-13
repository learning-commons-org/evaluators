"""Logging utilities for the Learning Commons Evaluators SDK.

Follows the "Configuring logging for a library" section of the Python logging HOWTO:

- A :class:`logging.NullHandler` is attached once to the logger named
  ``learning_commons_evaluators`` when this module is imported, so optional log
  calls never trigger "no handler" warnings if the host app does not configure
  logging.
- The library does not call :func:`logging.basicConfig` or otherwise configure
  the root logger.
- By default, :class:`~learning_commons_evaluators.schemas.config.EvaluatorConfig`
  uses the package logger ``learning_commons_evaluators`` so messages propagate
  to the root like typical libraries. Use :func:`create_silent_logger` when
  passing ``logger=`` if you need to discard SDK log lines entirely.
- Applications attach handlers to the root or to ``learning_commons_evaluators``,
  adjust levels (e.g. suppress the SDK while the app is at DEBUG), pass a custom
  :class:`~logging.Logger` through config, or use :func:`create_logger` for a
  small stream-handler helper.
"""

from __future__ import annotations

import logging

Logger = logging.Logger

SDK_LOGGER_NAME = "learning_commons_evaluators"


def _has_non_null_handler(logger: logging.Logger) -> bool:
    return any(not isinstance(h, logging.NullHandler) for h in logger.handlers)


def _install_library_null_handler() -> None:
    """Attach NullHandler to the SDK root logger once (stdlib library pattern)."""
    root = logging.getLogger(SDK_LOGGER_NAME)
    if not any(isinstance(h, logging.NullHandler) for h in root.handlers):
        root.addHandler(logging.NullHandler())


_install_library_null_handler()


def get_logger(name: str | None = None) -> logging.Logger:
    """Return the SDK root logger or a child (``learning_commons_evaluators.<name>``).

    Does not add handlers or change levels; configuration is left to the
    application or to :func:`create_logger`.
    """
    if name is None:
        return logging.getLogger(SDK_LOGGER_NAME)
    return logging.getLogger(f"{SDK_LOGGER_NAME}.{name}")


def create_logger(
    name: str | None = None,
    level: int = logging.WARNING,
    handler: logging.Handler | None = None,
    *,
    use_logger: logging.Logger | None = None,
) -> logging.Logger:
    """Return ``use_logger`` unchanged, or configure an SDK subtree logger.

    When no ``use_logger`` is given, sets *level* and attaches *handler*, or a
    :class:`logging.StreamHandler` if there is no non-:class:`~logging.NullHandler`
    handler yet (the import-time NullHandler alone does not count).

    Intended for applications and quick debugging, not for internal SDK calls.
    """
    if use_logger is not None:
        return use_logger

    logger = get_logger(name)
    logger.setLevel(level)

    if handler is not None:
        logger.addHandler(handler)
    elif not _has_non_null_handler(logger):
        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(level)
        stream_handler.setFormatter(logging.Formatter("[%(levelname)s] %(name)s: %(message)s"))
        logger.addHandler(stream_handler)

    return logger


def create_silent_logger() -> logging.Logger:
    """Logger that discards all records (no propagation). Use for ``logger=`` opt-out."""
    logger = logging.getLogger(f"{SDK_LOGGER_NAME}.silent")
    for h in list(logger.handlers):
        logger.removeHandler(h)
    logger.addHandler(logging.NullHandler())
    logger.propagate = False
    return logger


def format_error(error: BaseException) -> str:
    """Format an exception for logging."""
    return f"{type(error).__name__}: {error}"
