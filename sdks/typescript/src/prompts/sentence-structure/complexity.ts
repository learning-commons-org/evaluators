import { loadPrompt } from '../../utils/prompts';

/**
 * System prompt for sentence structure complexity evaluation
 * Loaded from: prompts/sentence-structure/complexity-system.txt
 */
const SYSTEM_PROMPT_COMPLEXITY_TEMPLATE = loadPrompt('sentence-structure/complexity-system.txt');

/**
 * Get the system prompt for sentence structure complexity evaluation
 * @returns The system prompt
 */
export function getSystemPromptComplexity(): string {
  return SYSTEM_PROMPT_COMPLEXITY_TEMPLATE;
}

/**
 * User prompt template for complexity evaluation
 * Loaded from: prompts/sentence-structure/complexity-user.txt
 */
const USER_PROMPT_COMPLEXITY_TEMPLATE = loadPrompt('sentence-structure/complexity-user.txt');

/**
 * Grade-specific rubrics
 */
const RUBRIC_GRADE_3 = loadPrompt('sentence-structure/rubric-grade-3.txt');
const RUBRIC_GRADE_4 = loadPrompt('sentence-structure/rubric-grade-4.txt');
const RUBRIC_GRADES_5_12 = loadPrompt('sentence-structure/rubric-grades-5-12.txt');

/**
 * Get the appropriate rubric based on grade level
 * @param grade - The target grade level (K-12)
 * @returns The rubric text for the grade level
 */
export function getRubricForGrade(grade: string): string {
  if (grade === '3') {
    return RUBRIC_GRADE_3;
  } else if (grade === '4') {
    return RUBRIC_GRADE_4;
  } else if (['5', '6', '7', '8', '9', '10', '11', '12'].includes(grade)) {
    return RUBRIC_GRADES_5_12;
  } else {
    // K, 1, 2 - no specific rubric, use general principles
    return 'No specific rubric available for this grade. Use general linguistic principles.';
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
    .replace('{excerpt}', excerpt);
}
