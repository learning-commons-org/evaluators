// GENERATED — do not edit directly.
// Source: ../../evals/feedback/ela-writing/strength-acknowledgment/output_schema.json
//         ../../evals/feedback/ela-writing/strength-acknowledgment/input_schema.json
// Regenerate: npm run generate:schemas

import { z } from 'zod';

/** What this evaluator accepts, from its input schema. */
export type StrengthAcknowledgmentInput = {
  /** The student's written response. */
  "student_text": string;
  /** The teacher's feedback to the student. */
  "feedback_text": string;
};

// prettier-ignore
export const StrengthAcknowledgmentOutputSchema = z.object({ "reasoning": z.string().describe("Step-by-step reasoning before the final answer: assess the student response against the task goal, then judge whether the teacher feedback meets the criterion."), "key_features": z.object({ "presence_of_praise": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Presence of praise that is specific and authentic"), "specificity": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Specificity of the acknowledgment rather than generic praise"), "anchoring_to_evidence": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Anchoring to evidence in the student response"), "process_vs_trait_framing": z.object({ "met": z.union([z.literal(0), z.literal(1)]).describe("1 if this key feature is satisfied by the feedback, 0 otherwise."), "justification": z.string().describe("One or two sentences grounding the met/not-met decision in the specific student response and teacher feedback.") }).strict().describe("Process-vs-trait framing") }).strict().describe("Per-key-feature assessment; each feature judged independently."), "proposed_adjustment": z.string().describe("How the teacher feedback could be modified to meet the criterion. If it already meets the criterion, say so briefly."), "quality_score": z.union([z.literal(0), z.literal(1)]).describe("Overall: 1 if the feedback meets the criterion, 0 otherwise.") }).strict();

export type StrengthAcknowledgmentResult = z.infer<typeof StrengthAcknowledgmentOutputSchema>;
