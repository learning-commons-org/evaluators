import { describe, it, expect } from 'vitest';
import { BatchedLCEvaluationSchema } from '../../../src/schemas/academic-standards-alignment/mathematics/math-standards-alignment.js';

// The verdict's feedback key is required and nullable, as the contract declares it (DSCR-2453).
const verdict = { lc_id: 'lc-1', reasoning: 'r', answer: 'Yes' as const };

describe('math standards alignment verdict feedback', () => {
  it('rejects a verdict without the feedback key', () => {
    expect(BatchedLCEvaluationSchema.safeParse({ evaluations: [verdict] }).success).toBe(false);
  });

  it('accepts a null feedback for an aligned verdict', () => {
    expect(BatchedLCEvaluationSchema.safeParse({ evaluations: [{ ...verdict, feedback: null }] }).success).toBe(true);
  });

  it('accepts text feedback', () => {
    expect(BatchedLCEvaluationSchema.safeParse({ evaluations: [{ ...verdict, feedback: 'Revise it.' }] }).success).toBe(true);
  });
});
