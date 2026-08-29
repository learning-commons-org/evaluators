import { describe, it, expect } from 'vitest';
import { SentenceStructureEvaluator } from '../../src/evaluators/sentence-structure.js';
import { ConfigurationError } from '../../src/errors.js';
import { Provider } from '../../src/evaluators/base.js';

/**
 * modelOverride integration tests (live API)
 *
 * Uses SentenceStructureEvaluator as the vehicle — simplest single-provider evaluator.
 * These tests are about the override feature, not sentence structure evaluation quality.
 *
 * To run:
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';

// A missing key when integration tests were explicitly requested is a
// misconfiguration, not a reason to quietly pass — matches batch/anthropic-provider.
if (RUN_INTEGRATION && !process.env.OPENAI_API_KEY) {
  throw new Error('OPENAI_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}

const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const TEST_TIMEOUT_MS = 2 * 60 * 1000;

const SAMPLE_TEXT =
  'The mitochondria is the powerhouse of the cell. It produces energy through a process called cellular respiration.';

describeIntegration('modelOverride — model validity (live API)', () => {
  it('succeeds with a valid model override', async () => {
    const evaluator = new SentenceStructureEvaluator({
      openaiApiKey: process.env.OPENAI_API_KEY!,
      modelOverride: { provider: Provider.OpenAI, model: 'gpt-4o-mini' },
      telemetry: false,
    });

    const result = await evaluator.evaluate({ text: SAMPLE_TEXT, grade_level: '5' });
    expect(result.result.answer).toBeDefined();
    expect(result.metadata.model).toMatch(/^openai:gpt-4o-mini/);
  }, TEST_TIMEOUT_MS);

  it('throws ConfigurationError for a non-existent model override', async () => {
    const evaluator = new SentenceStructureEvaluator({
      openaiApiKey: process.env.OPENAI_API_KEY!,
      modelOverride: { provider: Provider.OpenAI, model: 'gpt-this-model-does-not-exist-9999' },
      telemetry: false,
    });

    await expect(evaluator.evaluate({ text: SAMPLE_TEXT, grade_level: '5' })).rejects.toThrow(ConfigurationError);
  }, TEST_TIMEOUT_MS);
});
