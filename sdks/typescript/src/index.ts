// Core types and schemas
export type {
  EvaluationResult,
  EvaluationMetadata,
  EvaluationTokenUsage,
  EvaluationFailure,
} from './schemas/index.js';

export { TextComplexityLevel, GradeBand } from './schemas/index.js';
export { readOutcome, type Outcome } from './schemas/index.js';

// Error types
export {
  EvaluatorError,
  ConfigurationError,
  InputValidationError,
  StandardNotFoundError,
  EvaluationError,
  LLMOutputProcessingError,
  DependencyError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  RequestTimeoutError,
  LLMProviderError,
  KnowledgeGraphError,
  type DependencyId,
  type DependencyErrorOptions,
} from './errors.js';

// Knowledge Graph
export { Jurisdiction, StandardsCatalog, normalizeStatementCode } from './knowledge-graph/index.js';
export type {
  StandardsCatalogConfig,
  StandardsLookupOptions,
  CodeValidation,
  CodeResolutionStatus,
  StandardCandidate,
  AcademicStandard,
  StandardInfo,
} from './knowledge-graph/index.js';

// Logger
export type { Logger, LogContext } from './logger.js';
export { LogLevel } from './logger.js';

// Provider types (for implementing custom providers)
export type {
  LLMProvider,
  LLMRequest,
  LLMResponse,
  TextGenerationResponse,
  Message,
  ProviderConfig,
} from './providers/index.js';

export { Providers } from './providers/index.js';

// Sentence structure exports
export type {
  SentenceAnalysis,
  ComplexityClassification,
  SentenceFeatures,
} from './schemas/sentence-structure.js';

export {
  SentenceAnalysisSchema,
  ComplexityClassificationSchema,
} from './schemas/sentence-structure.js';

// Vocabulary Complexity exports
export type { VocabularyComplexityInternal } from './schemas/vocabulary-complexity.js';

// Background Knowledge Demands exports
export type { BackgroundKnowledgeDemandsInternal } from './schemas/background-knowledge-demands.js';

// Meaning Directness exports
export type { MeaningDirectnessInternal } from './schemas/meaning-directness.js';

// Grade Level Appropriateness exports
export type { GradeLevelAppropriatenessInternal } from './schemas/grade-level-appropriateness.js';

export { GradeLevelAppropriatenessOutputSchema } from './schemas/grade-level-appropriateness.js';

// Purpose Clarity exports
export type { PurposeClarityInternal } from './schemas/purpose-clarity.js';

// Reference Knowledge Demands exports
export type { ReferenceKnowledgeDemandsInternal } from './schemas/reference-knowledge-demands.js';

// Organizational Structure exports
export type { OrganizationalStructureInternal } from './schemas/organizational-structure.js';

export {
  VocabularyComplexityEvaluator,
  evaluateVocabularyComplexity,
  SentenceStructureEvaluator,
  evaluateSentenceStructure,
  BackgroundKnowledgeDemandsEvaluator,
  evaluateBackgroundKnowledgeDemands,
  MeaningDirectnessEvaluator,
  evaluateMeaningDirectness,
  GradeLevelAppropriatenessEvaluator,
  evaluateGradeLevelAppropriateness,
  PurposeClarityEvaluator,
  evaluatePurposeClarity,
  ReferenceKnowledgeDemandsEvaluator,
  evaluateReferenceKnowledgeDemands,
  OrganizationalStructureEvaluator,
  evaluateOrganizationalStructure,
  MathStandardsAlignmentEvaluator,
  evaluateMathStandardsAlignment,
  type MathStandardsAlignmentEvaluatorConfig,
  type LearningComponentResult,
  type StandardAlignmentResult,
  type QuestionItem,
  type QuestionBankResult,
  type QuestionResult,
  type QuestionBankOptions,
  Provider,
  type BaseEvaluatorConfig,
  type ModelOverride,
  type TelemetryOptions,
  type EvaluatorMetadata,
} from './evaluators/index.js';

// Features
export {
  calculateFleschKincaidGrade,
  calculateReadabilityMetrics,
  addEngineeredFeatures,
  featuresToJSON,
  type ReadabilityMetrics,
} from './features/index.js';
