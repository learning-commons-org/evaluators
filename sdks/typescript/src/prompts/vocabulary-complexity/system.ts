import SYSTEM_PROMPT_GRADES_3_4 from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/grades-3-4-system.txt';
import SYSTEM_PROMPT_OTHER_GRADES from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/other-grades-system.txt';
import CONFIG from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/config.json';
import { requireConditionValues } from '../../evaluators/multi-step.js';
import { requireStep } from '../../evaluators/single-step.js';

/** Which grades take the grades-3-4 branch, from the step's own declared condition. */
const GRADES_34 = requireConditionValues(
  requireStep(CONFIG.steps, 'vocab_complexity_grades_3_4', CONFIG.evaluator.name),
  CONFIG.evaluator.name,
);

/**
 * The system prompt for a grade's branch.
 *
 * Which grades take which branch is read from `config.json` rather than restated here — the
 * same fact drives the model choice and the user prompt, and three hardcoded copies of it
 * would drift independently.
 *
 * @param grade - The target grade level
 * @returns The system prompt for that grade's branch
 */
export function getSystemPrompt(grade: string): string {
  return GRADES_34.includes(grade) ? SYSTEM_PROMPT_GRADES_3_4 : SYSTEM_PROMPT_OTHER_GRADES;
}
