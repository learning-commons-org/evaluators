import Anthropic from '@anthropic-ai/sdk';

export const EVALUATE_TEXT_COMPLEXITY: Anthropic.Tool = {
  name: 'evaluate_text_complexity',
  description: `Evaluates vocabulary AND sentence structure complexity of a text passage relative to a specific grade level.
Returns scores on the scale: slightly_complex | moderately_complex | very_complex | exceedingly_complex.
Also returns detailed reasoning explaining which specific words or sentence patterns drive the score.
Use this to understand what makes a text too hard or too easy for a given grade, and to verify modifications.`,
  input_schema: {
    type: 'object',
    properties: {
      text: { type: 'string', description: 'The text passage to evaluate' },
      grade: { type: 'string', description: 'Grade level to evaluate against (3–12)' },
    },
    required: ['text', 'grade'],
    additionalProperties: false,
  },
};

export const EVALUATE_GRADE_LEVEL: Anthropic.Tool = {
  name: 'evaluate_grade_level',
  description: `Independently determines the grade band of a text passage without needing a target grade.
Returns one of: K-1 | 2-3 | 4-5 | 6-8 | 9-10 | 11-CCR.
This is a holistic check — it captures background knowledge assumptions and conceptual density that vocabulary/sentence scores alone miss.
Use this as the final gate after text_complexity passes, to confirm the text truly feels appropriate for the target grade.`,
  input_schema: {
    type: 'object',
    properties: {
      text: { type: 'string', description: 'The text passage to evaluate' },
    },
    required: ['text'],
    additionalProperties: false,
  },
};

export const SUBMIT_VARIANT: Anthropic.Tool = {
  name: 'submit_variant',
  description: `Submits a completed, verified text variant. Call this only after BOTH evaluation gates have passed:
1. evaluate_text_complexity shows appropriate scores for the target grade
2. evaluate_grade_level confirms the text is in the expected grade band.
You must submit exactly three variants: below, at, and above.`,
  input_schema: {
    type: 'object',
    properties: {
      level: {
        type: 'string',
        enum: ['below', 'at', 'above'],
        description: 'Which differentiation level this variant represents',
      },
      grade: {
        type: 'string',
        description: 'The grade this variant targets (e.g. "5" for N-1 if target is grade 6)',
      },
      text: {
        type: 'string',
        description: 'The complete final modified text for this variant',
      },
      rationale: {
        type: 'string',
        description: 'What was changed from the original and why, referencing the evaluation reasoning',
      },
    },
    required: ['level', 'grade', 'text', 'rationale'],
    additionalProperties: false,
  },
};

export const ALL_TOOLS: Anthropic.Tool[] = [
  EVALUATE_TEXT_COMPLEXITY,
  EVALUATE_GRADE_LEVEL,
  SUBMIT_VARIANT,
];
