import { describe, it, expect } from 'vitest';
import { readOutcome } from '../../../src/schemas/outcome.js';
import {
  MeaningDirectnessEvaluator,
  GradeLevelAppropriatenessEvaluator,
  SentenceStructureEvaluator,
  PurposeClarityEvaluator,
} from '../../../src/evaluators/index.js';

const COMPLEXITY_ID = MeaningDirectnessEvaluator.metadata.id;
const GLA_ID = GradeLevelAppropriatenessEvaluator.metadata.id;
const SENTENCE_ID = SentenceStructureEvaluator.metadata.id;

describe('readOutcome — by convention', () => {
  it('reads the single *_score property', () => {
    const outcome = readOutcome(COMPLEXITY_ID, {
      complexity_score: 'slightly_complex',
      reasoning: 'because',
    });

    expect(outcome).toEqual({ score: 'slightly_complex', reasoning: 'because' });
  });

  it('reads a *_score property it has never seen before', () => {
    // The convention is what makes a new evaluator work with no registration.
    const outcome = readOutcome('feedback.ela_writing.revision_accuracy', {
      quality_score: 1,
      reasoning: 'meets the criterion',
    });

    expect(outcome).toEqual({ score: '1', reasoning: 'meets the criterion' });
  });

  it('does not treat `reasoning` as the verdict', () => {
    expect(readOutcome(COMPLEXITY_ID, { reasoning: 'no verdict here' })).toEqual({
      score: '',
      reasoning: 'no verdict here',
    });
  });
});

describe('readOutcome — declared exceptions', () => {
  it('reads the grade band for Grade Level Appropriateness', () => {
    const outcome = readOutcome(GLA_ID, {
      grade: '4-5',
      alternative_grade: '6-8',
      reasoning: 'band fits',
    });

    expect(outcome.score).toBe('4-5');
  });

  it('prefers the declared field over a *_score property that happens to exist', () => {
    // Guards the precedence: GLA's payload gains a *_score field and the band must
    // still win, otherwise the report silently starts charting the wrong value.
    const outcome = readOutcome(GLA_ID, {
      grade: '4-5',
      confidence_score: 0.9,
      reasoning: 'band fits',
    });

    expect(outcome.score).toBe('4-5');
  });

  it('reads `answer` for Sentence Structure', () => {
    const outcome = readOutcome(SENTENCE_ID, {
      answer: 'Moderately complex',
      reasoning: 'mixed structures',
    });

    expect(outcome.score).toBe('Moderately complex');
  });

  it('applies no exception to an evaluator that follows the convention', () => {
    const outcome = readOutcome(PurposeClarityEvaluator.metadata.id, {
      complexity_score: 'very_complex',
      reasoning: 'implicit purpose',
    });

    expect(outcome.score).toBe('very_complex');
  });
});

describe('readOutcome — payloads with nothing to read', () => {
  // A missing verdict is a reporting gap. Throwing here would fail an evaluation
  // that already succeeded and whose payload the caller can still use.
  it.each([
    ['null', null],
    ['undefined', undefined],
    ['a string', 'not a payload'],
    ['a number', 7],
    ['an empty object', {}],
  ])('returns empty strings for %s', (_label, payload) => {
    expect(readOutcome(COMPLEXITY_ID, payload)).toEqual({ score: '', reasoning: '' });
  });

  it('returns an empty score when the declared field is absent', () => {
    expect(readOutcome(GLA_ID, { reasoning: 'no band' })).toEqual({
      score: '',
      reasoning: 'no band',
    });
  });

  it('coerces a non-string verdict to a string', () => {
    expect(readOutcome('feedback.ela_writing.tone_appropriateness', { quality_score: 0 }).score)
      .toBe('0');
  });

  it('ignores a non-string reasoning rather than coercing it', () => {
    // A report prints reasoning verbatim; "[object Object]" is worse than blank.
    expect(readOutcome(COMPLEXITY_ID, { complexity_score: 'x', reasoning: { a: 1 } })).toEqual({
      score: 'x',
      reasoning: '',
    });
  });

  it('treats a null verdict as absent', () => {
    expect(readOutcome(COMPLEXITY_ID, { complexity_score: null, reasoning: 'r' }).score).toBe('');
  });
});
