import SYSTEM_PROMPT from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/user.txt';
import CONFIG from '../../../../../evals/literacy/qualitative-text-complexity/intertextuality/config.json';
import { createPromptRenderers } from '../create-prompts.js';

export const { getSystemPrompt, getUserPrompt } = createPromptRenderers(
  SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CONFIG,
);
