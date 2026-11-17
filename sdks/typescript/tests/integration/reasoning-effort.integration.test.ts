import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { createProvider } from '../../src/providers/ai-sdk-provider.js';
import type { ReasoningEffort } from '../../src/providers/base.js';

/**
 * Every reasoning effort config.schema.json admits, sent to a real model of each provider.
 *
 * The unit wire tests show each value reaches the request; these show the vendor takes that
 * request, effort and structured output together, on a current model. Which of its
 * provider's values a model accepts is the model's own property, so each case states what
 * this model does: answers, or refuses with an error the caller sees. A refusal that turns
 * into an answer fails too, since a refused value must never be dropped or swapped. The
 * Python SDK's `test_reasoning_effort.py` holds the same table.
 *
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration -- reasoning-effort
 * ```
 * A provider whose key is not set is skipped.
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
const TIMEOUT_MS = 2 * 60 * 1000;

const SCHEMA = z.object({ total: z.number() });
const MESSAGES = [
  { role: 'system' as const, content: 'Answer in the JSON shape requested.' },
  { role: 'user' as const, content: 'What is 2 + 3?' },
];

/** One model per provider and, for each value its provider admits, whether it answers. */
const CASES = {
  openai: {
    key: 'OPENAI_API_KEY',
    model: 'gpt-5.5',
    efforts: { none: true, minimal: false, low: true, medium: true, high: true, xhigh: true, max: true },
  },
  anthropic: {
    key: 'ANTHROPIC_API_KEY',
    model: 'claude-haiku-5-5',
    efforts: { low: true, medium: true, high: true, xhigh: true, max: true },
  },
  google: {
    key: 'GOOGLE_API_KEY',
    model: 'gemini-3.6-flash',
    efforts: { minimal: true, low: true, medium: true, high: true },
  },
} as const;

for (const [type, { key, model, efforts }] of Object.entries(CASES)) {
  const apiKey = process.env[key];
  const run = RUN_INTEGRATION && apiKey ? describe : describe.skip;

  run(`reasoning effort live: ${type} ${model}`, () => {
    for (const [effort, answers] of Object.entries(efforts)) {
      it(
        `${answers ? 'answers' : 'refuses'} at ${effort}`,
        async () => {
          const provider = createProvider({ type: type as keyof typeof CASES, model, apiKey, maxRetries: 0 });
          const call = provider.generateStructured({
            messages: MESSAGES,
            schema: SCHEMA,
            reasoningEffort: effort as ReasoningEffort,
          });
          if (!answers) {
            await expect(call).rejects.toThrow(/effort|reasoning|thinking/i);
            return;
          }
          expect((await call).data.total).toBe(5);
        },
        TIMEOUT_MS,
      );
    }
  });
}
