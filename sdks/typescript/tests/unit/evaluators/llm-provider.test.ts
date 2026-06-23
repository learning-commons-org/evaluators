import { describe, it, expect, vi } from 'vitest';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/grade-level-appropriateness.js';
import { Provider } from '../../../src/evaluators/base.js';
import { ConfigurationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Unit tests for the `llmProvider` config option (bring-your-own-provider).
 *
 * Mirrors the Python SDK's `llm_provider` injection: implement the provider
 * interface, inject the instance, and the evaluator routes every LLM call
 * through it — no built-in API keys, no createProvider factory.
 *
 * These tests deliberately do NOT mock `createProvider`: a correctly injected
 * `llmProvider` must bypass it entirely, so the fake provider below is the only
 * model path exercised.
 */

const GLA_DATA = {
  grade: '6-8',
  alternative_grade: '4-5',
  scaffolding_needed: 'Pre-teach vocabulary; use diagrams',
  reasoning: 'Middle-school-appropriate science prose.',
};

const SAMPLE_TEXT =
  'The mitochondria is the powerhouse of the cell. It produces energy through a process ' +
  'called cellular respiration in eukaryotic organisms.';

function makeFakeProvider(label = 'vertex:gemini-2.5-pro') {
  const generateStructured = vi.fn().mockResolvedValue({
    data: GLA_DATA,
    model: label,
    usage: { inputTokens: 100, outputTokens: 50 },
    latencyMs: 10,
  });
  const provider: LLMProvider = {
    label,
    generateStructured,
    generateText: vi.fn().mockResolvedValue({
      text: '',
      usage: { inputTokens: 0, outputTokens: 0 },
      latencyMs: 0,
    }),
  };
  return { provider, generateStructured };
}

describe('llmProvider — bring-your-own-provider', () => {
  it('constructs with no API key when llmProvider is set', () => {
    const { provider } = makeFakeProvider();
    expect(
      () => new GradeLevelAppropriatenessEvaluator({ llmProvider: provider, telemetry: false })
    ).not.toThrow();
  });

  it('routes evaluation through the injected provider', async () => {
    const { provider, generateStructured } = makeFakeProvider();
    const evaluator = new GradeLevelAppropriatenessEvaluator({
      llmProvider: provider,
      telemetry: false,
    });

    const result = await evaluator.evaluate(SAMPLE_TEXT);

    expect(generateStructured).toHaveBeenCalledTimes(1);
    expect(result.score).toBe('6-8');
    expect(result.metadata.model).toBe('vertex:gemini-2.5-pro');
    // The injected provider is the one in use, not a createProvider-built one.
    // @ts-expect-error accessing private property for testing
    expect(evaluator.provider).toBe(provider);
  });

  it('tolerates ambient API keys (they are simply unused)', () => {
    const { provider } = makeFakeProvider();
    expect(
      () =>
        new GradeLevelAppropriatenessEvaluator({
          llmProvider: provider,
          googleApiKey: 'ambient-key-from-env',
          telemetry: false,
        })
    ).not.toThrow();
  });

  it('throws when both llmProvider and modelOverride are set', () => {
    const { provider } = makeFakeProvider();
    expect(
      () =>
        new GradeLevelAppropriatenessEvaluator({
          llmProvider: provider,
          modelOverride: { provider: Provider.OpenAI, model: 'gpt-4o' },
          telemetry: false,
        })
    ).toThrow(ConfigurationError);
  });
});
