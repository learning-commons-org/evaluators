import SYSTEM_PROMPT_GRADES_3_4 from '../../../../../evals/student-facing-text/ela-reading/vocabulary/grades-3-4-system.txt';
import SYSTEM_PROMPT_OTHER_GRADES from '../../../../../evals/student-facing-text/ela-reading/vocabulary/other-grades-system.txt';

/**
 * Get the appropriate system prompt based on grade level
 * @param grade - The target grade level (3-12)
 * @returns The system prompt for the grade level
 */
export function getSystemPrompt(grade: string): string {
  // Grades 3-4 use the GRADES_3_4 prompt
  if (grade === '3' || grade === '4') {
    return SYSTEM_PROMPT_GRADES_3_4;
  }

  // All other grades (5-12) use OTHER_GRADES prompt
  return SYSTEM_PROMPT_OTHER_GRADES;
}
