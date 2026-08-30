// Core types and schemas
export type {
  EvaluationResult,
  EvaluationMetadata,
  EvaluationTokenUsage,
} from './schemas/index.js';
export type { GradeBand } from './schemas/index.js';
export { readOutcome, type Outcome, type DeclaredOutcome } from './schemas/index.js';

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

// Sentence structure exports
export {
  SentenceStructureOutputSchema,
  type SentenceStructureResult,
} from './schemas/student-facing-text/ela-reading/sentence-structure.js';

// Its intermediate types: the first step's analysis, and the features computed from it.
// `ComplexityClassification` is gone — the final output is `SentenceStructureResult`.
export {
  SentenceAnalysisSchema,
  type SentenceAnalysis,
  type SentenceFeatures,
} from './schemas/student-facing-text/ela-reading/sentence-structure-steps.js';

// Vocabulary Complexity exports
export type { VocabularyComplexityResult } from './schemas/student-facing-text/ela-reading/vocabulary-complexity.js';

// Background Knowledge Demands exports
export type { BackgroundKnowledgeDemandsResult } from './schemas/student-facing-text/ela-reading/background-knowledge-demands.js';

// Meaning Directness exports
export type { MeaningDirectnessResult } from './schemas/student-facing-text/ela-reading/meaning-directness.js';

// Grade Level Appropriateness exports
export type { GradeLevelAppropriatenessResult } from './schemas/student-facing-text/ela-reading/grade-level-appropriateness.js';

export { GradeLevelAppropriatenessOutputSchema } from './schemas/student-facing-text/ela-reading/grade-level-appropriateness.js';
export { BackgroundKnowledgeDemandsOutputSchema } from './schemas/student-facing-text/ela-reading/background-knowledge-demands.js';
export { MeaningDirectnessOutputSchema } from './schemas/student-facing-text/ela-reading/meaning-directness.js';
export { OrganizationalStructureOutputSchema } from './schemas/student-facing-text/ela-reading/organizational-structure.js';
export { PurposeClarityOutputSchema } from './schemas/student-facing-text/ela-reading/purpose-clarity.js';
export { ReferenceKnowledgeDemandsOutputSchema } from './schemas/student-facing-text/ela-reading/reference-knowledge-demands.js';
export { VocabularyComplexityOutputSchema } from './schemas/student-facing-text/ela-reading/vocabulary-complexity.js';

// Purpose Clarity exports
export type { PurposeClarityResult } from './schemas/student-facing-text/ela-reading/purpose-clarity.js';

// Reference Knowledge Demands exports
export type { ReferenceKnowledgeDemandsResult } from './schemas/student-facing-text/ela-reading/reference-knowledge-demands.js';

// Organizational Structure exports
export type { OrganizationalStructureResult } from './schemas/student-facing-text/ela-reading/organizational-structure.js';

// Feedback exports
export type { RevisionAccuracyResult } from './schemas/feedback/ela-writing/revision-accuracy.js';
export { RevisionAccuracyOutputSchema } from './schemas/feedback/ela-writing/revision-accuracy.js';
export type { RevisionActionabilityResult } from './schemas/feedback/ela-writing/revision-actionability.js';
export { RevisionActionabilityOutputSchema } from './schemas/feedback/ela-writing/revision-actionability.js';
export type { RevisionManageabilityResult } from './schemas/feedback/ela-writing/revision-manageability.js';
export { RevisionManageabilityOutputSchema } from './schemas/feedback/ela-writing/revision-manageability.js';
export type { StrengthAcknowledgmentResult } from './schemas/feedback/ela-writing/strength-acknowledgment.js';
export { StrengthAcknowledgmentOutputSchema } from './schemas/feedback/ela-writing/strength-acknowledgment.js';
export type { StudentResponseSpecificityResult } from './schemas/feedback/ela-writing/student-response-specificity.js';
export { StudentResponseSpecificityOutputSchema } from './schemas/feedback/ela-writing/student-response-specificity.js';
export type { ToneAppropriatenessResult } from './schemas/feedback/ela-writing/tone-appropriateness.js';
export { ToneAppropriatenessOutputSchema } from './schemas/feedback/ela-writing/tone-appropriateness.js';
export type { WithholdingAnswersResult } from './schemas/feedback/ela-writing/withholding-answers.js';
export { WithholdingAnswersOutputSchema } from './schemas/feedback/ela-writing/withholding-answers.js';

export {
  VocabularyComplexityEvaluator,
  evaluateVocabularyComplexity,
  type BackgroundKnowledgeDemandsInput,
  type GradeLevelAppropriatenessInput,
  type MathStandardsAlignmentInput,
  type MeaningDirectnessInput,
  type OrganizationalStructureInput,
  type PurposeClarityInput,
  type ReferenceKnowledgeDemandsInput,
  type RevisionAccuracyInput,
  type RevisionActionabilityInput,
  type RevisionManageabilityInput,
  type SentenceStructureInput,
  type StrengthAcknowledgmentInput,
  type StudentResponseSpecificityInput,
  type ToneAppropriatenessInput,
  type VocabularyComplexityInput,
  type WithholdingAnswersInput,
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
  RevisionAccuracyEvaluator,
  evaluateRevisionAccuracy,
  RevisionActionabilityEvaluator,
  evaluateRevisionActionability,
  RevisionManageabilityEvaluator,
  evaluateRevisionManageability,
  StrengthAcknowledgmentEvaluator,
  evaluateStrengthAcknowledgment,
  StudentResponseSpecificityEvaluator,
  evaluateStudentResponseSpecificity,
  ToneAppropriatenessEvaluator,
  evaluateToneAppropriateness,
  WithholdingAnswersEvaluator,
  evaluateWithholdingAnswers,
  MathStandardsAlignmentEvaluator,
  evaluateMathStandardsAlignment,
  type MathStandardsAlignmentEvaluatorConfig,
  type LearningComponentResult,
  type StandardAlignmentResult,
  type MathStandardsAlignmentResult,
  type QuestionItem,
  type QuestionBankResult,
  type QuestionResult,
  type QuestionBankOptions,
  Provider,
  type BaseEvaluatorConfig,
  type ModelOverride,
  type TelemetryOptions,
  type EvaluatorMetadata,
  getEvaluators,
  getEvaluator,
} from './evaluators/index.js';

// Features
export {
  calculateFleschKincaidGrade,
  calculateReadabilityMetrics,
  addEngineeredFeatures,
  featuresToJSON,
  type ReadabilityMetrics,
} from './features/index.js';
