import { loadPrompt } from '../../utils/prompts';

/**
 * System prompt for vocabulary complexity evaluation (Grades 3-4)
 * Loaded from: prompts/vocabulary/grades-3-4-system.txt
 */
const SYSTEM_PROMPT_GRADES_3_4 = loadPrompt('vocabulary/grades-3-4-system.txt');

/**
 * System prompt for vocabulary complexity evaluation (Other grades: K-2, 5-12)
 * Loaded from: prompts/vocabulary/other-grades-system.txt
 */
const SYSTEM_PROMPT_OTHER_GRADES = loadPrompt('vocabulary/other-grades-system.txt');

/**
 * Get the appropriate system prompt based on grade level
 * @param grade - The target grade level (K-12)
 * @returns The system prompt for the grade level
 */
export function getSystemPrompt(grade: string): string {
  // Grades 3-4 use the GRADES_3_4 prompt
  if (grade === '3' || grade === '4') {
    return SYSTEM_PROMPT_GRADES_3_4;
  }

  // All other grades (K, 1, 2, 5-12) use OTHER_GRADES prompt
  return SYSTEM_PROMPT_OTHER_GRADES;
}
