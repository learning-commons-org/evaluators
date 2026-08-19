import SYSTEM_PROMPT_TEMPLATE from '../../../../../evals/literacy/ela-reading/grade-level-appropriateness/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/literacy/ela-reading/grade-level-appropriateness/user.txt';

/**
 * Get the system prompt for grade level appropriateness evaluation
 * @returns The system prompt
 */
export function getSystemPrompt(): string {
  return SYSTEM_PROMPT_TEMPLATE;
}

/**
 * Get the user prompt with the text to evaluate
 * @param text - The text to evaluate for grade level appropriateness
 * @returns The formatted user prompt
 */
export function getUserPrompt(text: string): string {
  return USER_PROMPT_TEMPLATE
    .replace('{text}', text)
    .replace('{format_instructions}', '');
}
