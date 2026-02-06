import { loadPrompt } from '../../utils/prompts.js';

/**
 * System prompt for grade level appropriateness evaluation
 * Loaded from: prompts/grade-level-appropriateness/system.txt
 */
const SYSTEM_PROMPT_TEMPLATE = loadPrompt('grade-level-appropriateness/system.txt');

/**
 * Get the system prompt for grade level appropriateness evaluation
 * @returns The system prompt
 */
export function getSystemPrompt(): string {
  return SYSTEM_PROMPT_TEMPLATE;
}

/**
 * User prompt template for grade level appropriateness evaluation
 * Loaded from: prompts/grade-level-appropriateness/user.txt
 */
const USER_PROMPT_TEMPLATE = loadPrompt('grade-level-appropriateness/user.txt');

/**
 * Get the user prompt with the text to evaluate
 * @param text - The text to evaluate for grade level appropriateness
 * @returns The formatted user prompt
 */
export function getUserPrompt(text: string): string {
  return USER_PROMPT_TEMPLATE.replace('{text}', text);
}
