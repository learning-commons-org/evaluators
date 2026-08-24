import { PurposeOutputSchema, type PurposeInternal } from '../schemas/purpose.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/purpose/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { Provider, type BaseEvaluatorConfig } from './base.js';
import {
  SingleStepRubricEvaluator,
  findEvaluationStep,
  findFkImplementation,
  supportedGradesFrom,
} from './single-step-rubric.js';
import CONFIG from '../../../../evals/prompts/purpose/config.json';
import INPUT_SCHEMA from '../../../../evals/prompts/purpose/input_schema.json';

const STEP = findEvaluationStep(CONFIG);

// Grade range from input_schema — needed for static metadata, so defined at module level.
const GRADE_MIN = INPUT_SCHEMA.properties.grade_level.minimum;
const GRADE_MAX = INPUT_SCHEMA.properties.grade_level.maximum;

export type PurposeComplexityLevel = TextComplexityLevel | 'More context needed';

// Maps snake_case LLM output → SDK-standard sentence case score.
const COMPLEXITY_SCORE_DISPLAY: Record<PurposeInternal['complexity_score'], PurposeComplexityLevel> = {
  'slightly_complex': 'Slightly complex',
  'moderately_complex': 'Moderately complex',
  'very_complex': 'Very complex',
  'exceedingly_complex': 'Exceedingly complex',
  'more_context_needed': 'More context needed',
};

export class PurposeEvaluator extends SingleStepRubricEvaluator<PurposeComplexityLevel, PurposeInternal> {
  static readonly metadata = {
    id: CONFIG.evaluator.id,
    name: CONFIG.evaluator.name,
    description: CONFIG.evaluator.description,
    supportedGrades: supportedGradesFrom(GRADE_MIN, GRADE_MAX),
    defaultProviders: [Provider.Google] as const,
  };

  constructor(config: BaseEvaluatorConfig) {
    super(config, {
      id: CONFIG.evaluator.id,
      displayName: 'Purpose',
      step: STEP,
      gradeMin: GRADE_MIN,
      gradeMax: GRADE_MAX,
      defaultProvider: Provider.Google,
      fkImplementation: findFkImplementation(CONFIG),
      outputSchema: PurposeOutputSchema,
      scoreDisplay: COMPLEXITY_SCORE_DISPLAY,
      getSystemPrompt,
      getUserPrompt,
    });
  }
}

export async function evaluatePurpose(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<PurposeComplexityLevel, PurposeInternal>> {
  return new PurposeEvaluator(config).evaluate(text, grade);
}
