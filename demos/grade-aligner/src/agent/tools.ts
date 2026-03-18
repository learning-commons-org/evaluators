import Anthropic from '@anthropic-ai/sdk';

export const EVALUATE_TEXT_COMPLEXITY: Anthropic.Tool = {
  name: 'evaluate_text_complexity',
  description: `Evaluates vocabulary AND sentence structure complexity of a text passage relative to a specific grade level.
Returns scores on the scale: slightly_complex | moderately_complex | very_complex | exceedingly_complex.
Also returns detailed reasoning identifying the specific words and sentence patterns driving the score.
Use this as a diagnostic — the reasoning tells you what to change, the score gives a rough direction.`,
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
This is your primary gate — it tells you where the text actually sits and whether you have reached the target band.`,
  input_schema: {
    type: 'object',
    properties: {
      text: { type: 'string', description: 'The text passage to evaluate' },
    },
    required: ['text'],
    additionalProperties: false,
  },
};

export const RECORD_ITERATION: Anthropic.Tool = {
  name: 'record_iteration',
  description: `Records a verified forward step — an adapted text where evaluate_grade_level confirmed movement toward the target band.
Call this after each GLA evaluation that shows progress in the right direction.
Do NOT call this for adaptations that did not move the band, moved the wrong way, or overshot the target.`,
  input_schema: {
    type: 'object',
    properties: {
      text: { type: 'string', description: 'The adapted text for this verified step' },
      gla_band: { type: 'string', description: 'The GLA band confirmed by evaluate_grade_level for this text' },
      reasoning: { type: 'string', description: 'What was changed in this step and why, referencing the complexity evaluation results' },
    },
    required: ['text', 'gla_band', 'reasoning'],
    additionalProperties: false,
  },
};

export const SUBMIT_ALIGNED_TEXT: Anthropic.Tool = {
  name: 'submit_aligned_text',
  description: `Submits the final grade-aligned text. Call only when evaluate_grade_level returns a band that contains the target grade N.
Include a rationale that summarises the full alignment journey.`,
  input_schema: {
    type: 'object',
    properties: {
      text: { type: 'string', description: 'The final aligned text' },
      rationale: { type: 'string', description: 'Summary of the full alignment journey — what changed overall and how each step contributed' },
    },
    required: ['text', 'rationale'],
    additionalProperties: false,
  },
};

export const ALL_TOOLS: Anthropic.Tool[] = [
  EVALUATE_TEXT_COMPLEXITY,
  EVALUATE_GRADE_LEVEL,
  RECORD_ITERATION,
  SUBMIT_ALIGNED_TEXT,
];
