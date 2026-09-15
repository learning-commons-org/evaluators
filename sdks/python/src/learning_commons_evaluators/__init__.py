"""Learning Commons Evaluators – Python SDK for educational text evaluators.

The package is being rebuilt on the shared ``evals/`` contracts and the SDK specification.
This release of the surface carries the canonical error taxonomy and the logger; the
bundled contracts live in :mod:`learning_commons_evaluators.contracts` and the provider
layer in :mod:`learning_commons_evaluators.providers`. The rebuilt evaluators follow.
"""

# Bind __version__ first so consumers reading it during package init never see AttributeError.
from learning_commons_evaluators.version import __description__, __version__  # noqa: I001

# Errors (SDK spec §6.1)
from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    DependencyError,
    EvaluationError,
    EvaluatorError,
    InputValidationError,
    KnowledgeGraphError,
    LLMOutputProcessingError,
    LLMProviderError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    StandardNotFoundError,
    wrap_provider_error,
)

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
    "AuthenticationError",
    "ConfigurationError",
    "DependencyError",
    "EvaluationError",
    "EvaluatorError",
    "InputValidationError",
    "KnowledgeGraphError",
    "LLMOutputProcessingError",
    "LLMProviderError",
    "Logger",
    "NetworkError",
    "RateLimitError",
    "RequestTimeoutError",
    "SDK_LOGGER_NAME",
    "StandardNotFoundError",
    "create_logger",
    "create_silent_logger",
    "get_logger",
    "wrap_provider_error",
]
