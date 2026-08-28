import SYSTEM_PROMPT from '../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/user.txt';
import CONFIG from '../../../../../evals/student-facing-text/ela-reading/reference-knowledge-demands/config.json';
import { createPromptRenderers } from '../create-prompts.js';

export const { getSystemPrompt, getUserPrompt } = createPromptRenderers(
  SYSTEM_PROMPT, USER_PROMPT_TEMPLATE, CONFIG,
);
