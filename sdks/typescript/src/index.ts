// Core types and schemas
export type {
  EvaluationResult,
  EvaluationMetadata,
  BatchEvaluationResult,
  BatchSummary,
  EvaluationError,
} from './schemas/index.js';

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
} from './schemas/sentence-structure.js';

export {
  SentenceAnalysisSchema,
  ComplexityClassificationSchema,
} from './schemas/sentence-structure.js';

// Vocabulary exports
export type {
  VocabularyComplexity,
  VocabularyComplexityLevel,
} from './schemas/vocabulary.js';

export {
  VocabularyEvaluator,
  evaluateVocabulary,
  type VocabularyEvaluatorConfig,
  SentenceStructureEvaluator,
  evaluateSentenceStructure,
  type SentenceStructureEvaluatorConfig,
  type BaseEvaluatorConfig,
  type TelemetryOptions,
} from './evaluators/index.js';

// Features
export {
  calculateFleschKincaidGrade,
  calculateReadabilityMetrics,
  addEngineeredFeatures,
  featuresToJSON,
  type ReadabilityMetrics,
} from './features/index.js';
