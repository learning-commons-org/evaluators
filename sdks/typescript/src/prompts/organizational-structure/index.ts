import SYSTEM_PROMPT from '../../../../../evals/literacy/qualitative-text-complexity/organizational-structure/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/literacy/qualitative-text-complexity/organizational-structure/user.txt';
import CONFIG from '../../../../../evals/literacy/qualitative-text-complexity/organizational-structure/config.json';
import { createPromptRenderers } from '../create-prompts.js';

export const { getSystemPrompt, getUserPrompt } = createPromptRenderers(
  SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CONFIG,
);
