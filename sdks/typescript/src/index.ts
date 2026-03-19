// Core types and schemas
export type {
  EvaluationResult,
  EvaluationMetadata,
  EvaluationError,
} from './schemas/index.js';

export { TextComplexityLevel, GradeBand } from './schemas/index.js';

// Error types
export {
  EvaluatorError,
  ConfigurationError,
  ValidationError,
  APIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
} from './errors.js';

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

// Sentence structure exports
export type {
  SentenceAnalysis,
  ComplexityClassification,
  SentenceFeatures,
  SentenceStructureInternal,
} from './schemas/sentence-structure.js';

export {
  SentenceAnalysisSchema,
  ComplexityClassificationSchema,
} from './schemas/sentence-structure.js';

// Vocabulary exports
export type { VocabularyInternal } from './schemas/vocabulary.js';

// Subject Matter Knowledge exports
export type { SmkInternal } from './schemas/smk.js';

// Conventionality exports
export type { ConventionalityInternal } from './schemas/conventionality.js';

// Grade Level Appropriateness exports
export type { GradeLevelAppropriatenessInternal } from './schemas/grade-level-appropriateness.js';

export { GradeLevelAppropriatenessSchema } from './schemas/grade-level-appropriateness.js';

export {
  VocabularyEvaluator,
  evaluateVocabulary,
  SentenceStructureEvaluator,
  evaluateSentenceStructure,
  SmkEvaluator,
  evaluateSmk,
  ConventionalityEvaluator,
  evaluateConventionality,
  GradeLevelAppropriatenessEvaluator,
  evaluateGradeLevelAppropriateness,
  TextComplexityEvaluator,
  evaluateTextComplexity,
  type TextComplexityResult,
  type BaseEvaluatorConfig,
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
