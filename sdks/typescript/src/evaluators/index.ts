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
} from './student-facing-text/ela-reading/vocabulary-complexity.js';

export {
  SentenceStructureEvaluator,
  evaluateSentenceStructure,
} from './student-facing-text/ela-reading/sentence-structure.js';

export {
  GradeLevelAppropriatenessEvaluator,
  evaluateGradeLevelAppropriateness,
} from './student-facing-text/ela-reading/grade-level-appropriateness.js';

export {
  BackgroundKnowledgeDemandsEvaluator,
  evaluateBackgroundKnowledgeDemands,
} from './student-facing-text/ela-reading/background-knowledge-demands.js';

export {
  MeaningDirectnessEvaluator,
  evaluateMeaningDirectness,
} from './student-facing-text/ela-reading/meaning-directness.js';

export {
  PurposeClarityEvaluator,
  evaluatePurposeClarity,
} from './student-facing-text/ela-reading/purpose-clarity.js';

export {
  ReferenceKnowledgeDemandsEvaluator,
  evaluateReferenceKnowledgeDemands,
} from './student-facing-text/ela-reading/reference-knowledge-demands.js';

export {
  OrganizationalStructureEvaluator,
  evaluateOrganizationalStructure,
} from './student-facing-text/ela-reading/organizational-structure.js';

export {
  RevisionAccuracyEvaluator,
  evaluateRevisionAccuracy,
} from './feedback/ela-writing/revision-accuracy.js';

export {
  RevisionActionabilityEvaluator,
  evaluateRevisionActionability,
} from './feedback/ela-writing/revision-actionability.js';

export {
  RevisionManageabilityEvaluator,
  evaluateRevisionManageability,
} from './feedback/ela-writing/revision-manageability.js';

export {
  StrengthAcknowledgmentEvaluator,
  evaluateStrengthAcknowledgment,
} from './feedback/ela-writing/strength-acknowledgment.js';

export {
  StudentResponseSpecificityEvaluator,
  evaluateStudentResponseSpecificity,
} from './feedback/ela-writing/student-response-specificity.js';

export {
  ToneAppropriatenessEvaluator,
  evaluateToneAppropriateness,
} from './feedback/ela-writing/tone-appropriateness.js';

export {
  WithholdingAnswersEvaluator,
  evaluateWithholdingAnswers,
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
} from './academic-standards-alignment/mathematics/math-standards-alignment.js';
