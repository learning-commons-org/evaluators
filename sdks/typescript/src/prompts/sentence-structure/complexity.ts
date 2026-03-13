import SYSTEM_PROMPT_COMPLEXITY_TEMPLATE from '../../../../../evals/prompts/sentence-structure/complexity-system.txt';
import USER_PROMPT_COMPLEXITY_TEMPLATE from '../../../../../evals/prompts/sentence-structure/complexity-user.txt';
import RUBRIC_GRADE_3 from '../../../../../evals/prompts/sentence-structure/rubric-grade-3.txt';
import RUBRIC_GRADE_4 from '../../../../../evals/prompts/sentence-structure/rubric-grade-4.txt';
import RUBRIC_GRADES_5_12 from '../../../../../evals/prompts/sentence-structure/rubric-grades-5-12.txt';

/**
 * Get the system prompt for sentence structure complexity evaluation
 * @returns The system prompt
 */
export function getSystemPromptComplexity(): string {
  return SYSTEM_PROMPT_COMPLEXITY_TEMPLATE;
}

/**
 * Get the appropriate rubric based on grade level
 * @param grade - The target grade level (3-12)
 * @returns The rubric text for the grade level
 */
export function getRubricForGrade(grade: string): string {
  if (grade === '3') {
    return RUBRIC_GRADE_3;
  } else if (grade === '4') {
    return RUBRIC_GRADE_4;
  } else {
    return RUBRIC_GRADES_5_12;
  }
}

/**
 * Generate the user prompt for complexity evaluation
 * @param sentenceFeatures - JSON string of sentence features
 * @param grade - The target grade level
 * @param excerpt - The original text excerpt
 * @returns The formatted user prompt
 */
export function getUserPromptComplexity(
  sentenceFeatures: string,
  grade: string,
  excerpt: string
): string {
  const rubric = getRubricForGrade(grade);

  return USER_PROMPT_COMPLEXITY_TEMPLATE
    .replace('{sentence_features}', sentenceFeatures)
    .replace('{grade}', grade)
    .replace('{rubric}', rubric)
    .replace('{excerpt}', excerpt)
    .replace('{format_instructions}', '');
}
