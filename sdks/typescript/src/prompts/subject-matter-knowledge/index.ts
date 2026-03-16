import SYSTEM_PROMPT from '../../../../../evals/prompts/subject-matter-knowledge/system.txt';
import USER_PROMPT_TEMPLATE from '../../../../../evals/prompts/subject-matter-knowledge/user.txt';

/**
 * Get the SMK evaluator system prompt
 */
export function getSystemPrompt(): string {
  return SYSTEM_PROMPT;
}

/**
 * Generate the user prompt for SMK evaluation
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
