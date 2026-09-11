// GENERATED — do not edit directly.
// Source: ../../evals/feedback/ela-writing/student-response-specificity/output_schema.json
//         ../../evals/feedback/ela-writing/student-response-specificity/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type StudentResponseSpecificityInput = {
  /** The student's written response. */
  "student_text": string;
  /** The teacher's feedback to the student. */
  "feedback_text": string;
};

// prettier-ignore
export const StudentResponseSpecificityOutputSchema = z.object({ "reasoning": z.string().describe("Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion."), "key_features": z.object({ "specific_reference_to_student_work": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Feedback should clearly reference or build on the student's specific idea, wording, or use of evidence"), "not_generic_or_template_based": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Feedback should not be a stock phrase that could apply to any response"), "engage_based_on_accurate_understanding": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Engages with the student's actual response, rather than something the student did not actually say or attempt. Demonstrates accurate understanding of what the student wrote.") }).strict().describe("Per-key-feature assessment; each feature judged independently."), "proposed_adjustment": z.string().describe("How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly."), "quality_score": z.union([z.literal(0), z.literal(1)]).describe("Overall: 1 if the feedback meets the criterion, 0 otherwise.") }).strict();

export type StudentResponseSpecificityResult = z.infer<typeof StudentResponseSpecificityOutputSchema>;
