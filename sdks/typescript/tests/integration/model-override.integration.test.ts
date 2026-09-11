import { describe, it, expect } from 'vitest';
import { SentenceStructureEvaluator } from '../../src/evaluators/student-facing-text/ela-reading/sentence-structure.js';
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
    expect(result.result.complexity_score).toBeDefined();
    expect(result.metadata.model).toMatch(/^openai:gpt-4o-mini/);
  }, TEST_TIMEOUT_MS);

  // Each provider rejects an unknown model differently, and the classifier reaches the same
  // verdict by two different routes: OpenAI answers 400 and has to be read from the error
  // body (`param: 'model'`), while Anthropic and Google answer 404 and are classified on
  // status alone. Covering only OpenAI left the 404 route unexercised live, and vice versa.
  const REJECTION_CASES = [
    { provider: Provider.OpenAI, keyField: 'openaiApiKey', envVar: 'OPENAI_API_KEY', model: 'gpt-this-model-does-not-exist-9999' },
    { provider: Provider.Anthropic, keyField: 'anthropicApiKey', envVar: 'ANTHROPIC_API_KEY', model: 'claude-this-model-does-not-exist-9999' },
    { provider: Provider.Google, keyField: 'googleApiKey', envVar: 'GOOGLE_API_KEY', model: 'gemini-this-model-does-not-exist-9999' },
  ] as const;

  for (const { provider, keyField, envVar, model } of REJECTION_CASES) {
    const apiKey = process.env[envVar];

    it.skipIf(!apiKey)(
      `throws ConfigurationError for a non-existent ${provider} model override`,
      async () => {
        const evaluator = new SentenceStructureEvaluator({
          [keyField]: apiKey,
          modelOverride: { provider, model },
          telemetry: false,
        });

        await expect(evaluator.evaluate({ text: SAMPLE_TEXT, grade_level: '5' })).rejects.toThrow(
          ConfigurationError
        );
      },
      TEST_TIMEOUT_MS
    );
  }
});
