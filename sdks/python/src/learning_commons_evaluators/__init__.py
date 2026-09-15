"""Learning Commons Evaluators – Python SDK for educational text evaluators.

The 0.2.0 evaluators, settings machinery, and LangChain provider have been removed; the
package is being rebuilt on the shared ``evals/`` contracts and the SDK specification.
Until the rebuilt evaluators land, the public surface is the logger and the version.
"""

# Bind __version__ first so consumers reading it during package init never see AttributeError.
from learning_commons_evaluators.version import __description__, __version__  # noqa: I001

# Logger (uses Python standard logging)
from learning_commons_evaluators.logger import (
    SDK_LOGGER_NAME,
    Logger,
    create_logger,
    create_silent_logger,
    get_logger,
)

__all__ = [
    "__description__",
    "__version__",
    "Logger",
    "SDK_LOGGER_NAME",
    "create_logger",
    "create_silent_logger",
    "get_logger",
]
