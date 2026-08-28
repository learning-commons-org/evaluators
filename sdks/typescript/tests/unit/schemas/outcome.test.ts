import { describe, it, expect } from 'vitest';
import { readOutcome } from '../../../src/schemas/outcome.js';
import type { EvaluationResult } from '../../../src/schemas/index.js';
import {
  MeaningDirectnessEvaluator,
  GradeLevelAppropriatenessEvaluator,
  SentenceStructureEvaluator,
  PurposeClarityEvaluator,
} from '../../../src/evaluators/index.js';

const COMPLEXITY_ID = MeaningDirectnessEvaluator.metadata.id;
const GLA_ID = GradeLevelAppropriatenessEvaluator.metadata.id;
const SENTENCE_ID = SentenceStructureEvaluator.metadata.id;

/** Minimal envelope — readOutcome reads only `evaluator` and `result`. */
const envelope = (evaluator: string, result: unknown): EvaluationResult => ({
  evaluator,
  result,
  metadata: {
    model: 'stub:model',
    processingTimeMs: 0,
    tokenUsage: { inputTokens: 0, outputTokens: 0 },
  },
});

describe('readOutcome — by convention', () => {
  it('reads the single *_score property', () => {
    const outcome = readOutcome(
      envelope(COMPLEXITY_ID, { complexity_score: 'slightly_complex', reasoning: 'because' }),
    );

    expect(outcome).toEqual({ score: 'slightly_complex', reasoning: 'because' });
  });

  it('reads a *_score property it has never seen before', () => {
    // The convention is what makes a new evaluator work with no registration.
    const outcome = readOutcome(
      envelope('feedback.ela_writing.revision_accuracy', {
        quality_score: 1,
        reasoning: 'meets the criterion',
      }),
    );

    expect(outcome).toEqual({ score: '1', reasoning: 'meets the criterion' });
  });

  it('does not treat `reasoning` as the verdict', () => {
    const outcome = readOutcome(envelope(COMPLEXITY_ID, { reasoning: 'no verdict here' }));

    expect(outcome).toEqual({ score: undefined, reasoning: 'no verdict here' });
  });
});

describe('readOutcome — declared exceptions', () => {
  it('reads the grade band for Grade Level Appropriateness', () => {
    const outcome = readOutcome(
      envelope(GLA_ID, { grade: '4-5', alternative_grade: '6-8', reasoning: 'band fits' }),
    );

    expect(outcome.score).toBe('4-5');
  });

  it('prefers the declared field over a *_score property that happens to exist', () => {
    // Guards the precedence: GLA's payload gains a *_score field and the band must
    // still win, otherwise the report silently starts charting the wrong value.
    const outcome = readOutcome(
      envelope(GLA_ID, { grade: '4-5', confidence_score: 0.9, reasoning: 'band fits' }),
    );

    expect(outcome.score).toBe('4-5');
  });

  it('falls back to the convention once the declared field is gone', () => {
    // Sentence Structure's schema will be regenerated to `complexity_score`. If the
    // stale `answer` entry still took precedence the verdict would silently go empty;
    // instead the convention takes over and the entry becomes inert.
    const outcome = readOutcome(
      envelope(SENTENCE_ID, { complexity_score: 'moderately_complex', reasoning: 'mixed' }),
    );

    expect(outcome.score).toBe('moderately_complex');
  });

  it('reads `answer` for Sentence Structure', () => {
    const outcome = readOutcome(
      envelope(SENTENCE_ID, { answer: 'Moderately complex', reasoning: 'mixed structures' }),
    );

    expect(outcome.score).toBe('Moderately complex');
  });

  it('applies no exception to an evaluator that follows the convention', () => {
    const outcome = readOutcome(
      envelope(PurposeClarityEvaluator.metadata.id, {
        complexity_score: 'very_complex',
        reasoning: 'implicit purpose',
      }),
    );

    expect(outcome.score).toBe('very_complex');
  });
});

describe('readOutcome — payloads with nothing to read', () => {
  // An absent verdict is surfaced as undefined rather than rendered as an empty string:
  // it is a reporting gap, and throwing would fail an evaluation that already succeeded.
  it.each([
    ['null', null],
    ['undefined', undefined],
    ['a string', 'not a payload'],
    ['a number', 7],
    ['an empty object', {}],
    ['an array', [{ complexity_score: 'slightly_complex' }]],
  ])('returns an undefined score for %s', (_label, payload) => {
    expect(readOutcome(envelope(COMPLEXITY_ID, payload))).toEqual({
      score: undefined,
      reasoning: '',
    });
  });

  it('returns an undefined score when the declared field is absent', () => {
    expect(readOutcome(envelope(GLA_ID, { reasoning: 'no band' }))).toEqual({
      score: undefined,
      reasoning: 'no band',
    });
  });

  it('coerces a non-string verdict to a string', () => {
    const outcome = readOutcome(
      envelope('feedback.ela_writing.tone_appropriateness', { quality_score: 0 }),
    );

    expect(outcome.score).toBe('0');
  });

  it('ignores a non-string reasoning rather than coercing it', () => {
    // A report prints reasoning verbatim; "[object Object]" is worse than blank.
    const outcome = readOutcome(
      envelope(COMPLEXITY_ID, { complexity_score: 'x', reasoning: { a: 1 } }),
    );

    expect(outcome).toEqual({ score: 'x', reasoning: '' });
  });

  it('treats a null verdict as absent', () => {
    const outcome = readOutcome(
      envelope(COMPLEXITY_ID, { complexity_score: null, reasoning: 'r' }),
    );

    expect(outcome.score).toBeUndefined();
  });
});
