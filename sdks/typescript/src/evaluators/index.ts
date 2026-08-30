export { getEvaluators, getEvaluator } from './registry.js';

export {
  BaseEvaluator,
  Provider,
  type BaseEvaluatorConfig,
  type ModelOverride,
  type TelemetryOptions,
  type EvaluatorMetadata,
} from './base.js';

export {
  VocabularyComplexityEvaluator,
  evaluateVocabularyComplexity,
  type VocabularyComplexityInput,
} from './student-facing-text/ela-reading/vocabulary-complexity.js';

export {
  SentenceStructureEvaluator,
  evaluateSentenceStructure,
  type SentenceStructureInput,
} from './student-facing-text/ela-reading/sentence-structure.js';

export {
  GradeLevelAppropriatenessEvaluator,
  evaluateGradeLevelAppropriateness,
  type GradeLevelAppropriatenessInput,
} from './student-facing-text/ela-reading/grade-level-appropriateness.js';

export {
  BackgroundKnowledgeDemandsEvaluator,
  evaluateBackgroundKnowledgeDemands,
  type BackgroundKnowledgeDemandsInput,
} from './student-facing-text/ela-reading/background-knowledge-demands.js';

export {
  MeaningDirectnessEvaluator,
  evaluateMeaningDirectness,
  type MeaningDirectnessInput,
} from './student-facing-text/ela-reading/meaning-directness.js';

export {
  PurposeClarityEvaluator,
  evaluatePurposeClarity,
  type PurposeClarityInput,
} from './student-facing-text/ela-reading/purpose-clarity.js';

export {
  ReferenceKnowledgeDemandsEvaluator,
  evaluateReferenceKnowledgeDemands,
  type ReferenceKnowledgeDemandsInput,
} from './student-facing-text/ela-reading/reference-knowledge-demands.js';

export {
  OrganizationalStructureEvaluator,
  evaluateOrganizationalStructure,
  type OrganizationalStructureInput,
} from './student-facing-text/ela-reading/organizational-structure.js';

export {
  RevisionAccuracyEvaluator,
  evaluateRevisionAccuracy,
  type RevisionAccuracyInput,
} from './feedback/ela-writing/revision-accuracy.js';

export {
  RevisionActionabilityEvaluator,
  evaluateRevisionActionability,
  type RevisionActionabilityInput,
} from './feedback/ela-writing/revision-actionability.js';

export {
  RevisionManageabilityEvaluator,
  evaluateRevisionManageability,
  type RevisionManageabilityInput,
} from './feedback/ela-writing/revision-manageability.js';

export {
  StrengthAcknowledgmentEvaluator,
  evaluateStrengthAcknowledgment,
  type StrengthAcknowledgmentInput,
} from './feedback/ela-writing/strength-acknowledgment.js';

export {
  StudentResponseSpecificityEvaluator,
  evaluateStudentResponseSpecificity,
  type StudentResponseSpecificityInput,
} from './feedback/ela-writing/student-response-specificity.js';

export {
  ToneAppropriatenessEvaluator,
  evaluateToneAppropriateness,
  type ToneAppropriatenessInput,
} from './feedback/ela-writing/tone-appropriateness.js';

export {
  WithholdingAnswersEvaluator,
  evaluateWithholdingAnswers,
  type WithholdingAnswersInput,
} from './feedback/ela-writing/withholding-answers.js';

export {
  MathStandardsAlignmentEvaluator,
  evaluateMathStandardsAlignment,
  type MathStandardsAlignmentEvaluatorConfig,
  type LearningComponentResult,
  type StandardAlignmentResult,
  type QuestionItem,
  type QuestionBankResult,
  type QuestionResult,
  type QuestionBankOptions,
  type MathStandardsAlignmentInput,
} from './academic-standards-alignment/mathematics/math-standards-alignment.js';
