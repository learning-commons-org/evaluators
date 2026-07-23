import SYSTEM_PROMPT from '../../../../../../evals/standards/math-question-alignment/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../../evals/standards/math-question-alignment/user.txt';
import COARSE_FILTER_PROMPT_TEMPLATE from '../../../../../../evals/standards/math-question-alignment/coarse-filter-user.txt';
import CONFIG from '../../../../../../evals/standards/math-question-alignment/config.json';
import INPUT_SCHEMA from '../../../../../../evals/standards/math-question-alignment/input_schema.json';
import { createHash } from 'node:crypto';

const STEP_ID = 'evaluate_standards_alignment';
const _step = CONFIG.steps.find((s) => s.id === STEP_ID);
if (!_step) throw new Error(`Step "${STEP_ID}" not found in math-question-alignment config.json`);
export const STEP = _step;
export const EVALUATOR_ID: string = CONFIG.evaluator.id;

/** SHA-256 over all prompt files — stable cache key for downstream tools. */
export const PROMPT_CHECKSUM = createHash('sha256')
  .update([SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, COARSE_FILTER_PROMPT_TEMPLATE].join('\n---\n'), 'utf8')
  .digest('hex');

export const SUPPORTED_GRADES: readonly string[] = CONFIG.evaluator.supported_grades;
export const MAX_QUESTION_LENGTH: number = INPUT_SCHEMA.properties.question.maxLength;

const DETAIL_PLACEHOLDER_KEYS = Object.keys(STEP.prompt.placeholders) as string[];
const SYSTEM_PLACEHOLDER_KEYS: string[] = [];
const COARSE_PLACEHOLDER_KEYS = ['question', 'standards'];

function replace(template: string, keys: readonly string[], inputs: Record<string, string>): string {
  return keys.reduce(
    (text, key) => (key in inputs ? text.replaceAll(`{${key}}`, inputs[key]) : text),
    template,
  );
}

export function getSystemPrompt(inputs: Record<string, string>): string {
  return replace(SYSTEM_PROMPT, SYSTEM_PLACEHOLDER_KEYS, inputs);
}

export function getUserPrompt(inputs: Record<string, string>): string {
  return replace(USER_PROMPT_TEMPLATE, DETAIL_PLACEHOLDER_KEYS, inputs);
}

export function getCoarseFilterPrompt(inputs: Record<string, string>): string {
  return replace(COARSE_FILTER_PROMPT_TEMPLATE, COARSE_PLACEHOLDER_KEYS, inputs);
}
