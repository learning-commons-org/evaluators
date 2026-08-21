import SYSTEM_PROMPT from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/user.txt';
import CONFIG from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/config.json';

const STEP_ID = `evaluate_${CONFIG.evaluator.id.split('.').pop()}`;
const _step = CONFIG.steps.find(s => s.id === STEP_ID);
if (!_step) throw new Error(`Step "${STEP_ID}" not found in intertextuality config.json`);
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
