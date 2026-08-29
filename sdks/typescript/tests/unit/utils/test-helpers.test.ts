import { describe, it, expect, vi } from 'vitest';
import { runEvaluatorTest } from '../../utils/test-helpers.js';

/**
 * The integration harness compares a verdict it reads out of the result envelope. That
 * read is the thing most likely to go stale — a payload field gets renamed and every
 * comparison silently becomes `undefined` against a real expected value, which looks like
 * a quality regression rather than a harness fault. These run offline so the failure is
 * caught before any live call is spent.
 */

class FakeEvaluator {
  static readonly metadata = {
    id: 'demo.area.thing',
    outcome: { score: 'complexity_score', reasoning: 'reasoning' },
  };

  constructor(private readonly payload: Record<string, unknown>) {}

  evaluate = vi.fn(async () => ({
    evaluator: FakeEvaluator.metadata.id,
    result: this.payload,
    metadata: { model: 'x:y', processingTimeMs: 1, tokenUsage: { inputTokens: 1, outputTokens: 1 } },
  }));
}

const CASE = { id: 'T1', text: 'A passage.', grade: '5', expected: 'moderately_complex' };

describe('the integration harness reads the declared verdict', () => {
  it('extracts the field the contract names, not a top-level score', async () => {
    const evaluator = new FakeEvaluator({
      complexity_score: 'moderately_complex',
      reasoning: 'because',
    });

    const result = await runEvaluatorTest(CASE, { evaluator, maxAttempts: 1 });

    expect(result.allResults).toEqual(['moderately_complex']);
    expect(result.matched).toBe(true);
  });

  it('stops after the first match rather than spending the retry budget', async () => {
    const evaluator = new FakeEvaluator({
      complexity_score: 'moderately_complex',
      reasoning: 'because',
    });

    await runEvaluatorTest(CASE, { evaluator, maxAttempts: 3 });

    expect(evaluator.evaluate).toHaveBeenCalledTimes(1);
  });

  it('reports a genuine mismatch as the value returned, not as absent', async () => {
    const evaluator = new FakeEvaluator({ complexity_score: 'very_complex', reasoning: 'r' });

    const result = await runEvaluatorTest(CASE, { evaluator, maxAttempts: 1 });

    // The distinction that matters: a wrong answer, not a failed read.
    expect(result.allResults).toEqual(['very_complex']);
    expect(result.matched).toBe(false);
  });

  it('accepts an adjacent value when the expected one never arrives', async () => {
    const evaluator = new FakeEvaluator({ complexity_score: 'very_complex', reasoning: 'r' });

    const result = await runEvaluatorTest(
      { ...CASE, acceptable: ['very_complex'] },
      { evaluator, maxAttempts: 2 },
    );

    expect(result.matched).toBe(true);
    expect(result.matchType).toBe('acceptable');
  });

  it('omits grade_level for an evaluator whose schema declares none', async () => {
    // Grade Level Appropriateness takes only text; passing grade_level would be rejected
    // as an undeclared input, so the harness must not send it.
    const evaluator = new FakeEvaluator({ complexity_score: 'moderately_complex', reasoning: 'r' });

    await runEvaluatorTest({ id: 'T2', text: 'A passage.', expected: 'moderately_complex' }, {
      evaluator,
      maxAttempts: 1,
    });

    expect(evaluator.evaluate).toHaveBeenCalledWith({ text: 'A passage.' });
  });

  it('sends grade_level when the case carries one', async () => {
    const evaluator = new FakeEvaluator({ complexity_score: 'moderately_complex', reasoning: 'r' });

    await runEvaluatorTest(CASE, { evaluator, maxAttempts: 1 });

    expect(evaluator.evaluate).toHaveBeenCalledWith({ text: CASE.text, grade_level: CASE.grade });
  });

  it('still honours an explicit extractor for a non-verdict field', async () => {
    const evaluator = new FakeEvaluator({ complexity_score: 'x', reasoning: 'r', other: 'picked' });

    const result = await runEvaluatorTest(
      { ...CASE, expected: 'picked' },
      { evaluator, maxAttempts: 1, extractResult: (r) => String(r.result.other) },
    );

    expect(result.allResults).toEqual(['picked']);
  });
});
