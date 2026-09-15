"""Learning Commons Evaluators – Python SDK for educational text evaluators.

Every evaluator is built from its contract under ``evals/`` and shares one configuration
(:class:`EvaluatorConfig`), one result envelope (:class:`EvaluationResult`), and one error
taxonomy. Import evaluator classes, their input and output models, and the helpers below
from this package::

    from learning_commons_evaluators import PurposeClarityEvaluator, read_outcome

    evaluator = PurposeClarityEvaluator(google_api_key="...")
    evaluation = evaluator.evaluate_sync(text="...", grade_level=5)
    print(read_outcome(evaluation, PurposeClarityEvaluator.metadata.outcome).score)
"""

# Bind __version__ first so consumers reading it during package init never see AttributeError.
from learning_commons_evaluators.version import __description__, __version__  # noqa: I001

# Configuration (SDK spec §3)
from learning_commons_evaluators.config import EvaluatorConfig, ModelOverride, TelemetryOptions

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

# Evaluators and registry
from learning_commons_evaluators.evaluators import (
    BaseEvaluator,
    GradeLevelAppropriatenessEvaluator,
    PurposeClarityEvaluator,
    SingleStepEvaluator,
    ToneAppropriatenessEvaluator,
    get_evaluator,
    get_evaluators,
)

# Logger (uses Python standard logging)
from learning_commons_evaluators.logger import (
    SDK_LOGGER_NAME,
    Logger,
    create_logger,
    create_silent_logger,
    get_logger,
)
from learning_commons_evaluators.providers import LLMProvider, Provider

# Result envelope and metadata (SDK spec §5)
from learning_commons_evaluators.schemas import (
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
    EvaluatorMetadata,
    Outcome,
    read_outcome,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.tone_appropriateness import (
    ToneAppropriatenessInput,
    ToneAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.grade_level_appropriateness import (
    GradeLevelAppropriatenessInput,
    GradeLevelAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.purpose_clarity import (
    PurposeClarityInput,
    PurposeClarityOutput,
)

__all__ = [
    "__description__",
    "__version__",
    "AuthenticationError",
    "BaseEvaluator",
    "ConfigurationError",
    "DependencyError",
    "EvaluationError",
    "EvaluationMetadata",
    "EvaluationResult",
    "EvaluationTokenUsage",
    "EvaluatorConfig",
    "EvaluatorError",
    "EvaluatorMetadata",
    "GradeLevelAppropriatenessEvaluator",
    "GradeLevelAppropriatenessInput",
    "GradeLevelAppropriatenessOutput",
    "InputValidationError",
    "KnowledgeGraphError",
    "LLMOutputProcessingError",
    "LLMProvider",
    "LLMProviderError",
    "Logger",
    "ModelOverride",
    "NetworkError",
    "Outcome",
    "Provider",
    "PurposeClarityEvaluator",
    "PurposeClarityInput",
    "PurposeClarityOutput",
    "RateLimitError",
    "RequestTimeoutError",
    "SDK_LOGGER_NAME",
    "SingleStepEvaluator",
    "StandardNotFoundError",
    "TelemetryOptions",
    "ToneAppropriatenessEvaluator",
    "ToneAppropriatenessInput",
    "ToneAppropriatenessOutput",
    "create_logger",
    "create_silent_logger",
    "get_evaluator",
    "get_evaluators",
    "get_logger",
    "read_outcome",
    "wrap_provider_error",
]
