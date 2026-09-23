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

# Knowledge Graph client (D9): the one non-LLM dependency evaluators call
from learning_commons_evaluators.dependencies import (
    AcademicStandard,
    KnowledgeGraphClient,
    LearningComponent,
    LearningComponentSet,
    StandardMatch,
    normalize_statement_code,
)

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
    BackgroundKnowledgeDemandsEvaluator,
    BaseEvaluator,
    GradeLevelAppropriatenessEvaluator,
    MeaningDirectnessEvaluator,
    MultiStepEvaluator,
    OrganizationalStructureEvaluator,
    PurposeClarityEvaluator,
    ReferenceKnowledgeDemandsEvaluator,
    RevisionAccuracyEvaluator,
    RevisionActionabilityEvaluator,
    RevisionManageabilityEvaluator,
    SentenceStructureEvaluator,
    SingleStepEvaluator,
    StrengthAcknowledgmentEvaluator,
    StudentResponseSpecificityEvaluator,
    ToneAppropriatenessEvaluator,
    VocabularyComplexityEvaluator,
    WithholdingAnswersEvaluator,
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
from learning_commons_evaluators.schemas.kg_taxonomy import (
    AcademicSubject,
    GradeLevel,
    Jurisdiction,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_accuracy import (
    RevisionAccuracyInput,
    RevisionAccuracyOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_actionability import (
    RevisionActionabilityInput,
    RevisionActionabilityOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.revision_manageability import (
    RevisionManageabilityInput,
    RevisionManageabilityOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.strength_acknowledgment import (
    StrengthAcknowledgmentInput,
    StrengthAcknowledgmentOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.student_response_specificity import (
    StudentResponseSpecificityInput,
    StudentResponseSpecificityOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.tone_appropriateness import (
    ToneAppropriatenessInput,
    ToneAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.withholding_answers import (
    WithholdingAnswersInput,
    WithholdingAnswersOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.background_knowledge_demands import (
    BackgroundKnowledgeDemandsInput,
    BackgroundKnowledgeDemandsOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.grade_level_appropriateness import (
    GradeLevelAppropriatenessInput,
    GradeLevelAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.meaning_directness import (
    MeaningDirectnessInput,
    MeaningDirectnessOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.organizational_structure import (
    OrganizationalStructureInput,
    OrganizationalStructureOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.purpose_clarity import (
    PurposeClarityInput,
    PurposeClarityOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.reference_knowledge_demands import (
    ReferenceKnowledgeDemandsInput,
    ReferenceKnowledgeDemandsOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.sentence_structure import (
    SentenceStructureInput,
    SentenceStructureOutput,
)
from learning_commons_evaluators.schemas.text_complexity.ela_reading.vocabulary_complexity import (
    VocabularyComplexityInput,
    VocabularyComplexityOutput,
)

__all__ = [
    "__description__",
    "__version__",
    "AcademicStandard",
    "AcademicSubject",
    "AuthenticationError",
    "BackgroundKnowledgeDemandsEvaluator",
    "BackgroundKnowledgeDemandsInput",
    "BackgroundKnowledgeDemandsOutput",
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
    "GradeLevel",
    "GradeLevelAppropriatenessEvaluator",
    "GradeLevelAppropriatenessInput",
    "GradeLevelAppropriatenessOutput",
    "InputValidationError",
    "Jurisdiction",
    "KnowledgeGraphClient",
    "KnowledgeGraphError",
    "LLMOutputProcessingError",
    "LLMProvider",
    "LLMProviderError",
    "LearningComponent",
    "LearningComponentSet",
    "Logger",
    "MeaningDirectnessEvaluator",
    "MeaningDirectnessInput",
    "MeaningDirectnessOutput",
    "ModelOverride",
    "MultiStepEvaluator",
    "NetworkError",
    "OrganizationalStructureEvaluator",
    "OrganizationalStructureInput",
    "OrganizationalStructureOutput",
    "Outcome",
    "Provider",
    "PurposeClarityEvaluator",
    "PurposeClarityInput",
    "PurposeClarityOutput",
    "RateLimitError",
    "ReferenceKnowledgeDemandsEvaluator",
    "ReferenceKnowledgeDemandsInput",
    "ReferenceKnowledgeDemandsOutput",
    "RequestTimeoutError",
    "RevisionAccuracyEvaluator",
    "RevisionAccuracyInput",
    "RevisionAccuracyOutput",
    "RevisionActionabilityEvaluator",
    "RevisionActionabilityInput",
    "RevisionActionabilityOutput",
    "RevisionManageabilityEvaluator",
    "RevisionManageabilityInput",
    "RevisionManageabilityOutput",
    "SDK_LOGGER_NAME",
    "SentenceStructureEvaluator",
    "SentenceStructureInput",
    "SentenceStructureOutput",
    "SingleStepEvaluator",
    "StandardMatch",
    "StandardNotFoundError",
    "StrengthAcknowledgmentEvaluator",
    "StrengthAcknowledgmentInput",
    "StrengthAcknowledgmentOutput",
    "StudentResponseSpecificityEvaluator",
    "StudentResponseSpecificityInput",
    "StudentResponseSpecificityOutput",
    "TelemetryOptions",
    "ToneAppropriatenessEvaluator",
    "ToneAppropriatenessInput",
    "ToneAppropriatenessOutput",
    "VocabularyComplexityEvaluator",
    "VocabularyComplexityInput",
    "VocabularyComplexityOutput",
    "WithholdingAnswersEvaluator",
    "WithholdingAnswersInput",
    "WithholdingAnswersOutput",
    "create_logger",
    "create_silent_logger",
    "get_evaluator",
    "get_evaluators",
    "get_logger",
    "normalize_statement_code",
    "read_outcome",
    "wrap_provider_error",
]
