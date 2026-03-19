import SYSTEM_PROMPT from '../../../../../evals/prompts/conventionality/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/prompts/conventionality/user.txt';

/**
 * Get the Conventionality evaluator system prompt
 */
export function getSystemPrompt(): string {
  return SYSTEM_PROMPT;
}

/**
 * Generate the user prompt for Conventionality evaluation
 * @param text - The text to evaluate
 * @param grade - The target grade level
 * @param fkScore - Flesch-Kincaid grade level score
 */
export function getUserPrompt(text: string, grade: string, fkScore: number): string {
  return USER_PROMPT_TEMPLATE
    .replaceAll('{text}', text)
    .replaceAll('{grade}', grade)
    .replaceAll('{fk_score}', fkScore.toString());
}
