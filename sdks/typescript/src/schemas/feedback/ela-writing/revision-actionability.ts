// GENERATED — do not edit directly.
// Source: ../../evals/feedback/ela-writing/revision-actionability/output_schema.json
//         ../../evals/feedback/ela-writing/revision-actionability/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type RevisionActionabilityInput = {
  /** The student's written response. */
  "student_text": string;
  /** The teacher's feedback to the student. */
  "feedback_text": string;
};

// prettier-ignore
export const RevisionActionabilityOutputSchema = z.object({ "reasoning": z.string().describe("Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion."), "key_features": z.object({ "directive_verb_or_focused_question": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Presence of a directive verb or focused question"), "clarity_of_target": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Clarity of the target (what to revise)"), "specificity_of_next_move": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Specificity of the next move"), "reasonable_student_action": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Whether the student could reasonably act without further clarification") }).strict().describe("Per-key-feature assessment; each feature judged independently."), "proposed_adjustment": z.string().describe("How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly."), "quality_score": z.union([z.literal(0), z.literal(1)]).describe("Overall: 1 if the feedback meets the criterion, 0 otherwise.") }).strict();

export type RevisionActionabilityResult = z.infer<typeof RevisionActionabilityOutputSchema>;
