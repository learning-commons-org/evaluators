import { describe, it, expect } from 'vitest';
import { readOutcome, type DeclaredOutcome } from '../../../src/schemas/outcome.js';
import type { EvaluationResult } from '../../../src/schemas/index.js';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/index.js';

/**
 * `readOutcome` reads the evaluator's declared `outcome` block. There is no convention
 * to fall back on and no per-evaluator table, so these cover the declaration being
 * honoured, absent, or pointing at something the payload does not have.
 */

const envelope = (result: unknown): EvaluationResult => ({
  evaluator: MeaningDirectnessEvaluator.metadata.id,
  result,
  metadata: {
    model: 'stub:model',
    processingTimeMs: 0,
    tokenUsage: { inputTokens: 0, outputTokens: 0 },
  },
});

const COMPLEXITY: DeclaredOutcome = { score: 'complexity_score', reasoning: 'reasoning' };

describe('readOutcome — the declaration is honoured', () => {
  it('reads the declared properties', () => {
    const outcome = readOutcome(
      envelope({ complexity_score: 'slightly_complex', reasoning: 'because' }),
      COMPLEXITY,
    );

    expect(outcome).toEqual({ score: 'slightly_complex', reasoning: 'because' });
  });

  it('reads whatever the declaration names, with no convention involved', () => {
    // A grade band is a verdict too; nothing here recognises `_score` suffixes.
    const outcome = readOutcome(
      envelope({ grade_band: '4-5', reasoning: 'band fits' }),
      { score: 'grade_band', reasoning: 'reasoning' },
    );

    expect(outcome.score).toBe('4-5');
  });

  it('ignores a *_score property the declaration does not name', () => {
    // Guards against the old convention creeping back: only the declared field counts.
    const outcome = readOutcome(
      envelope({ grade_band: '4-5', confidence_score: 0.9, reasoning: 'r' }),
      { score: 'grade_band', reasoning: 'reasoning' },
    );

    expect(outcome.score).toBe('4-5');
  });

  it('coerces a non-string verdict to a string', () => {
    const outcome = readOutcome(
      envelope({ quality_score: 0, reasoning: 'r' }),
      { score: 'quality_score', reasoning: 'reasoning' },
    );

    expect(outcome.score).toBe('0');
  });

  it('reads a reasoning property under a different name', () => {
    const outcome = readOutcome(
      envelope({ complexity_score: 'x', rationale: 'why' }),
      { score: 'complexity_score', reasoning: 'rationale' },
    );

    expect(outcome.reasoning).toBe('why');
  });
});

describe('readOutcome — nothing to read', () => {
  // A missing verdict is a reporting gap, not a reason to fail an evaluation that
  // already succeeded, so these report absence rather than throwing.
  it('returns an undefined score when no outcome is declared', () => {
    const outcome = readOutcome(envelope({ complexity_score: 'slightly_complex' }), undefined);

    expect(outcome).toEqual({ score: undefined, reasoning: '' });
  });

  it('returns an undefined score when the declared property is absent', () => {
    const outcome = readOutcome(envelope({ reasoning: 'no verdict' }), COMPLEXITY);

    expect(outcome).toEqual({ score: undefined, reasoning: 'no verdict' });
  });

  it('treats a null verdict as absent', () => {
    const outcome = readOutcome(envelope({ complexity_score: null, reasoning: 'r' }), COMPLEXITY);

    expect(outcome.score).toBeUndefined();
  });

  it('ignores a non-string reasoning rather than coercing it', () => {
    // A report prints reasoning verbatim; "[object Object]" is worse than blank.
    const outcome = readOutcome(
      envelope({ complexity_score: 'x', reasoning: { a: 1 } }),
      COMPLEXITY,
    );

    expect(outcome).toEqual({ score: 'x', reasoning: '' });
  });

  it.each([
    ['null', null],
    ['undefined', undefined],
    ['a string', 'not a payload'],
    ['a number', 7],
    ['an array', [{ complexity_score: 'slightly_complex' }]],
  ])('returns an undefined score for %s', (_label, payload) => {
    expect(readOutcome(envelope(payload), COMPLEXITY)).toEqual({
      score: undefined,
      reasoning: '',
    });
  });
});

describe('every evaluator that declares an outcome exposes it', () => {
  it('carries the declaration on metadata', () => {
    // How the declaration reaches readOutcome: without this the contract is inert.
    expect(MeaningDirectnessEvaluator.metadata.outcome).toEqual({
      score: 'complexity_score',
      reasoning: 'reasoning',
    });
  });
});
