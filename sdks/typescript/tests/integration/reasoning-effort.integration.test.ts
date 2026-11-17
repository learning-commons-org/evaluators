import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { createProvider } from '../../src/providers/ai-sdk-provider.js';
import CONFIG_SCHEMA from '../../../../evals/_schemas/config.schema.json';

/**
 * Every reasoning effort config.schema.json admits, sent to a real model of each provider.
 *
 * The unit wire tests show each value reaches the request; these show the vendor takes that
 * request, effort and structured output together, on a current model. The values are read
 * from the schema, so a value added there is sent here too. Which of them a model accepts
 * is the model's own property, so each provider names the values its model refuses with an
 * error the caller sees; it answers the rest. A refusal that turns
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

const DEFS = CONFIG_SCHEMA.$defs;

/** One model per provider, its provider's values from the schema, and those it refuses. */
const CASES = {
  openai: { key: 'OPENAI_API_KEY', model: 'gpt-5.5', efforts: DEFS.ReasoningEffortOpenAI.enum, refused: ['minimal', 'max'] },
  anthropic: { key: 'ANTHROPIC_API_KEY', model: 'claude-haiku-5-5', efforts: DEFS.ReasoningEffortAnthropic.enum, refused: [] },
  google: { key: 'GOOGLE_API_KEY', model: 'gemini-3.6-flash', efforts: DEFS.ReasoningEffortGoogle.enum, refused: [] },
} as const;

for (const [type, { key, model, efforts, refused }] of Object.entries(CASES)) {
  // A refused value the schema no longer lists would never be sent, so it must be one of them.
  for (const value of refused as readonly string[]) {
    if (!(efforts as readonly string[]).includes(value)) {
      throw new Error(`${type}: refused "${value}" is not in config.schema.json's values`);
    }
  }
  const apiKey = process.env[key];
  const run = RUN_INTEGRATION && apiKey ? describe : describe.skip;

  run(`reasoning effort live: ${type} ${model}`, () => {
    for (const effort of efforts) {
      const answers = !(refused as readonly string[]).includes(effort);
      it(
        `${answers ? 'answers' : 'refuses'} at ${effort}`,
        async () => {
          const provider = createProvider({ type: type as keyof typeof CASES, model, apiKey, maxRetries: 0 });
          const call = provider.generateStructured({
            messages: MESSAGES,
            schema: SCHEMA,
            reasoningEffort: effort,
          });
          if (!answers) {
            // The refusal names the value, so it is this value being refused and not, say, the key.
            await expect(call).rejects.toThrow(`'${effort}'`);
            return;
          }
          expect((await call).data.total).toBe(5);
        },
        TIMEOUT_MS,
      );
    }
  });
}
