import USER_PROMPT_TEMPLATE_GRADES_3_4 from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/grades-3-4-user.txt';
import USER_PROMPT_TEMPLATE_OTHER_GRADES from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/other-grades-user.txt';
import CONFIG from '../../../../../evals/student-facing-text/ela-reading/vocabulary-complexity/config.json';
import { requireConditionValues, requirePreprocessing } from '../../evaluators/multi-step.js';
import { requireStep } from '../../evaluators/single-step.js';

/** Which branch a grade takes, and whether it binds `{fk_score}`, per the contract. */
const GRADES_34 = requireConditionValues(
  requireStep(CONFIG.steps, 'vocab_complexity_grades_3_4', CONFIG.evaluator.name),
  CONFIG.evaluator.name,
);
const FK_APPLIES_TO = requireConditionValues(
  requirePreprocessing(CONFIG, 'fk_score'),
  CONFIG.evaluator.name,
);

/**
 * Generate the user prompt for vocabulary complexity evaluation
 * @param text - The text to evaluate
 * @param studentGradeLevel - The student's grade level
 * @param studentBackgroundKnowledge - Background knowledge assumption
 * @param fkLevel - Flesch-Kincaid grade level; omitted for grades whose prompt does not bind it
 * @returns The formatted user prompt
 */
export function getUserPrompt(
  text: string,
  studentGradeLevel: string,
  studentBackgroundKnowledge: string,
  fkLevel?: number
): string {
  const template = GRADES_34.includes(studentGradeLevel)
    ? USER_PROMPT_TEMPLATE_GRADES_3_4
    : USER_PROMPT_TEMPLATE_OTHER_GRADES;

  const rendered = template
    .replaceAll('{grade_level}', studentGradeLevel)
    .replaceAll('{student_background_knowledge}', studentBackgroundKnowledge)
    .replaceAll('{text}', text);

  // Only the grades that declare the entry bind it. Substituting `undefined` for the rest
  // would put the string "undefined" into any template that happened to carry the token.
  return FK_APPLIES_TO.includes(studentGradeLevel) && fkLevel !== undefined
    ? rendered.replaceAll('{fk_score}', fkLevel.toString())
    : rendered;
}
