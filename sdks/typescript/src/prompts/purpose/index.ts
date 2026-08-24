import SYSTEM_PROMPT from '../../../../../evals/prompts/purpose/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/prompts/purpose/user.txt';
import CONFIG from '../../../../../evals/prompts/purpose/config.json';
import { createPromptRenderers } from '../create-prompts.js';

export const { getSystemPrompt, getUserPrompt } = createPromptRenderers(
  SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CONFIG,
);
