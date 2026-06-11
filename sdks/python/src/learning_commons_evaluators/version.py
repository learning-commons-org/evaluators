"""Package version and description. Isolated to avoid circular imports."""

try:
    from importlib.metadata import version

    __version__ = version("learning-commons-evaluators")
except Exception:
    __version__ = "0.2.0"

__description__ = "Python SDK for Learning Commons educational evaluators"
