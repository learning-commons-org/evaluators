import USER_PROMPT_TEMPLATE_GRADES_3_4 from '../../../../../evals/prompts/vocabulary/grades-3-4-user.txt';
import USER_PROMPT_TEMPLATE_OTHER_GRADES from '../../../../../evals/prompts/vocabulary/other-grades-user.txt';

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
    .replaceAll('{student_grade_level}', studentGradeLevel)
    .replaceAll('{student_background_knowledge}', studentBackgroundKnowledge)
    .replaceAll('{fk_level}', fkLevel.toString())
    .replaceAll('{text}', text);
}
