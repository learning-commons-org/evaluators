import { loadPrompt } from '../../utils/prompts';

/**
 * User prompt template for vocabulary complexity evaluation (Grades 3-4)
 * Loaded from: prompts/vocabulary/grades-3-4-user.txt
 */
const USER_PROMPT_TEMPLATE_GRADES_3_4 = loadPrompt('vocabulary/grades-3-4-user.txt');

/**
 * User prompt template for vocabulary complexity evaluation (Other grades: K-2, 5-12)
 * Loaded from: prompts/vocabulary/other-grades-user.txt
 */
const USER_PROMPT_TEMPLATE_OTHER_GRADES = loadPrompt('vocabulary/other-grades-user.txt');

/**
 * Generate the user prompt for vocabulary complexity evaluation
 * @param text - The text to evaluate
 * @param studentGradeLevel - The student's grade level
 * @param studentBackgroundKnowledge - Background knowledge assumption
 * @param fkLevel - Flesch-Kincaid grade level
 * @returns The formatted user prompt
 */
export function getUserPrompt(
  text: string,
  studentGradeLevel: string,
  studentBackgroundKnowledge: string,
  fkLevel: number
): string {
  // Select the appropriate template based on grade
  const template = studentGradeLevel === '3' || studentGradeLevel === '4'
    ? USER_PROMPT_TEMPLATE_GRADES_3_4
    : USER_PROMPT_TEMPLATE_OTHER_GRADES;

  return template
    .replace('{student_grade_level}', studentGradeLevel)
    .replace('{student_background_knowledge}', studentBackgroundKnowledge)
    .replace('{fk_level}', fkLevel.toString())
    .replace('{text}', text);
}
