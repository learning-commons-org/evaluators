import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
} from '../../../src/evaluators/index.js';
import { InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * The feedback family is the first to take two texts and no grade level, so what is worth
 * testing here is that input shape — the flow itself is covered by single-step.test.ts and
 * each evaluator's contract wiring by the conformance suite.
 */

const EVALUATORS = [
  RevisionAccuracyEvaluator,
  RevisionActionabilityEvaluator,
  RevisionManageabilityEvaluator,
  StrengthAcknowledgmentEvaluator,
  StudentResponseSpecificityEvaluator,
  ToneAppropriatenessEvaluator,
  WithholdingAnswersEvaluator,
].map((E) => ({ name: E.metadata.name, E }));

const STUDENT_TEXT = 'My dog is brown. He runs fast. I like him a lot because he is fun.';
const FEEDBACK_TEXT = 'Try adding a topic sentence so the reader knows your argument.';

function provider(): LLMProvider {
  return {
    label: 'openai:gpt-5.4-2026-03-05',
    generateStructured: vi.fn().mockResolvedValue({
      data: { quality_score: 1, reasoning: 'Meets the criterion.' },
      usage: { inputTokens: 11, outputTokens: 4 },
      latencyMs: 9,
    }),
    generateText: vi.fn(),
  };
}

function run(E: (typeof EVALUATORS)[number]['E'], p: LLMProvider) {
  return new (E as unknown as new (c: Record<string, unknown>) => {
    evaluate(i: Record<string, string>): Promise<{ evaluator: string; result: unknown }>;
  })({ llmProvider: p, telemetry: false }).evaluate({
    student_text: STUDENT_TEXT,
    feedback_text: FEEDBACK_TEXT,
  });
}

describe('the feedback family renders both of its texts', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each(EVALUATORS)('$name', async ({ E }) => {
    const p = provider();
    await run(E, p);

    const messages = vi.mocked(p.generateStructured).mock.calls[0][0].messages;
    const rendered = messages.map((m) => m.content).join('\n');

    // Both texts are declared placeholders, and the evaluator judges the second against
    // the first, so losing either silently changes the question.
    expect(rendered).toContain(STUDENT_TEXT);
    expect(rendered).toContain(FEEDBACK_TEXT);
    expect(rendered).not.toContain('{student_text}');
    expect(rendered).not.toContain('{feedback_text}');
  });
});

describe('the feedback family returns the envelope', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each(EVALUATORS)('$name', async ({ E }) => {
    const p = provider();
    const result = await run(E, p);

    expect(result.evaluator).toBe(E.metadata.id);
    expect(result.result).toEqual({ quality_score: 1, reasoning: 'Meets the criterion.' });
  });
});

describe('the feedback family requires both texts', () => {
  beforeEach(() => vi.clearAllMocks());

  it.each(EVALUATORS)('$name rejects a missing feedback_text', async ({ E }) => {
    const p = provider();
    const evaluator = new (E as unknown as new (c: Record<string, unknown>) => {
      evaluate(i: Record<string, string>): Promise<unknown>;
    })({ llmProvider: p, telemetry: false });

    await expect(evaluator.evaluate({ student_text: STUDENT_TEXT })).rejects.toThrow(
      InputValidationError,
    );
    expect(p.generateStructured).not.toHaveBeenCalled();
  });
});
