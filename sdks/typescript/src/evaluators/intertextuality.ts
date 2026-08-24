import { IntertextualityOutputSchema, type IntertextualityInternal } from '../schemas/intertextuality.js';
import { getSystemPrompt, getUserPrompt } from '../prompts/intertextuality/index.js';
import type { EvaluationResult, TextComplexityLevel } from '../schemas/index.js';
import { Provider, type BaseEvaluatorConfig } from './base.js';
import {
  SingleStepRubricEvaluator,
  findEvaluationStep,
  findFkImplementation,
  supportedGradesFrom,
} from './single-step-rubric.js';
import CONFIG from '../../../../evals/literacy/qualitative-text-complexity/intertextuality/config.json';
import INPUT_SCHEMA from '../../../../evals/literacy/qualitative-text-complexity/intertextuality/input_schema.json';

const STEP = findEvaluationStep(CONFIG);

// Grade range from input_schema — needed for static metadata, so defined at module level.
const GRADE_MIN = INPUT_SCHEMA.properties.grade_level.minimum;
const GRADE_MAX = INPUT_SCHEMA.properties.grade_level.maximum;

// Maps snake_case LLM output → SDK-standard sentence case score.
const COMPLEXITY_SCORE_DISPLAY: Record<IntertextualityInternal['complexity_score'], TextComplexityLevel> = {
  'slightly_complex': 'Slightly complex',
  'moderately_complex': 'Moderately complex',
  'very_complex': 'Very complex',
  'exceedingly_complex': 'Exceedingly complex',
};

export class IntertextualityEvaluator extends SingleStepRubricEvaluator<TextComplexityLevel, IntertextualityInternal> {
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
      displayName: 'Intertextuality',
      step: STEP,
      gradeMin: GRADE_MIN,
      gradeMax: GRADE_MAX,
      defaultProvider: Provider.Google,
      fkImplementation: findFkImplementation(CONFIG),
      outputSchema: IntertextualityOutputSchema,
      scoreDisplay: COMPLEXITY_SCORE_DISPLAY,
      getSystemPrompt,
      getUserPrompt,
    });
  }
}

export async function evaluateIntertextuality(
  text: string,
  grade: string,
  config: BaseEvaluatorConfig,
): Promise<EvaluationResult<TextComplexityLevel, IntertextualityInternal>> {
  return new IntertextualityEvaluator(config).evaluate(text, grade);
}
