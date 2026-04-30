"""Learning Commons Evaluators – Python SDK for educational text evaluators."""

from learning_commons_evaluators._version import __description__, __version__

# Config
from learning_commons_evaluators.config import (
    AnthropicPromptProviderConfig,
    EvaluatorConfig,
    GooglePromptProviderConfig,
    OpenAIPromptProviderConfig,
    PromptProviderConfig,
    PromptSettings,
    create_config,
    create_config_no_telemetry,
    create_config_telemetry_with_full_input,
)

# Errors
from learning_commons_evaluators.errors import (
    APIError,
    AuthenticationError,
    ConfigurationError,
    EvaluatorError,
    EvaluatorRetryableError,
    EvaluatorTimeoutError,
    NetworkError,
    RateLimitError,
    ValidationError,
    wrap_provider_error,
)

# Evaluators
from learning_commons_evaluators.evaluators import (
    BaseEvaluator,
    ConventionalityEvaluator,
    InputT,
    OutputT,
)
from learning_commons_evaluators.evaluators.conventionality import (
    ConventionalityEvaluationInput,
)

# Logger (uses Python standard logging)
from learning_commons_evaluators.logger import (
    SDK_LOGGER_NAME,
    Logger,
    create_logger,
    create_silent_logger,
    get_logger,
)
from learning_commons_evaluators.schemas.common_inputs import (
    GradeInputField,
    TextInputField,
)
from learning_commons_evaluators.schemas.config import EvaluationSettings, LlmProvider
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
    ConventionalityOutput,
)

# Schemas (core)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationAnswer,
    EvaluationExplanation,
    EvaluationInput,
    EvaluationResult,
    InputField,
)
from learning_commons_evaluators.schemas.input_specs import (
    AnyInputSpec,
    GradeInputSpec,
    InputSpec,
    TextInputSpec,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
    TokenUsage,
)
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityEvaluationInput,
)

__all__ = [
    "__description__",
    "__version__",
    "APIError",
    "AnthropicPromptProviderConfig",
    "AuthenticationError",
    "BaseEvaluator",
    "ConfigurationError",
    "ConventionalityEvaluationInput",
    "ConventionalityEvaluationSettings",
    "ConventionalityEvaluator",
    "ConventionalityOutput",
    "EvaluationAnswer",
    "EvaluationExplanation",
    "EvaluationInput",
    "EvaluationMetadata",
    "EvaluationResult",
    "EvaluationSettings",
    "EvaluatorConfig",
    "EvaluatorError",
    "EvaluatorMaturity",
    "EvaluatorMetadata",
    "EvaluatorRetryableError",
    "EvaluatorTimeoutError",
    "GooglePromptProviderConfig",
    "AnyInputSpec",
    "GradeInputField",
    "GradeInputSpec",
    "InputField",
    "InputSpec",
    "InputT",
    "TextInputSpec",
    "LlmProvider",
    "Logger",
    "NetworkError",
    "OpenAIPromptProviderConfig",
    "OutputT",
    "PromptProviderConfig",
    "PromptSettings",
    "RateLimitError",
    "SDK_LOGGER_NAME",
    "Status",
    "TextComplexityEvaluationInput",
    "TextInputField",
    "TokenUsage",
    "ValidationError",
    "create_config",
    "create_config_no_telemetry",
    "create_config_telemetry_with_full_input",
    "create_logger",
    "create_silent_logger",
    "get_logger",
    "wrap_provider_error",
]
