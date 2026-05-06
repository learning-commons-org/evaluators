import SYSTEM_PROMPT from '../../../../../evals/prompts/purpose/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/prompts/purpose/user.txt';
import CONFIG from '../../../../../evals/prompts/purpose/config.json';

const STEP_ID = `evaluate_${CONFIG.evaluator.id.split('.').pop()}`;
const _step = CONFIG.steps.find(s => s.id === STEP_ID);
if (!_step) throw new Error(`Step "${STEP_ID}" not found in purpose config.json`);
const PLACEHOLDER_KEYS = Object.keys(_step.prompt.placeholders);

function applyPlaceholders(template: string, inputs: Record<string, string>): string {
  return PLACEHOLDER_KEYS.reduce(
    (text, key) => key in inputs ? text.replaceAll(`{${key}}`, inputs[key]) : text,
    template,
  );
}

export function getSystemPrompt(inputs: Record<string, string>): string {
  return applyPlaceholders(SYSTEM_PROMPT, inputs);
}

export function getUserPrompt(inputs: Record<string, string>): string {
  return applyPlaceholders(USER_PROMPT_TEMPLATE, inputs);
}
