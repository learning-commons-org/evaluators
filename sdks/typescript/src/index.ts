// Core types and schemas
export type {
  EvaluationResult,
  EvaluationMetadata,
  BatchEvaluationResult,
  BatchSummary,
  EvaluationError,
} from './schemas/index.js';

export { ComplexityLevel, GradeLevel } from './schemas/index.js';

// Error types
export {
  EvaluatorError,
  ValidationError,
  APIError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  TimeoutError,
  wrapProviderError,
} from './errors.js';

// Logger
export type { Logger, LogContext } from './logger.js';
export { LogLevel, createLogger, formatError } from './logger.js';

// Provider exports
export type {
  LLMProvider,
  LLMRequest,
  LLMResponse,
  TextGenerationResponse,
  Message,
  ProviderConfig,
} from './providers/index.js';

export { VercelAIProvider, createProvider } from './providers/index.js';

// Vocabulary exports
export type {
  VocabularyComplexity,
  VocabularyComplexityLevel,
  BackgroundKnowledge,
} from './schemas/vocabulary.js';

export { VocabularyComplexitySchema } from './schemas/vocabulary.js';

export {
  VocabularyEvaluator,
  evaluateVocabulary,
  type VocabularyEvaluatorConfig,
  type BaseEvaluatorConfig,
  type TelemetryOptions,
} from './evaluators/index.js';

// Features
export {
  calculateFleschKincaidGrade,
  calculateReadabilityMetrics,
  type ReadabilityMetrics,
} from './features/index.js';
