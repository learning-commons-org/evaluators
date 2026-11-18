import { describe, it, expect } from 'vitest';
import { z } from 'zod';
import { createProvider } from '../../src/providers/ai-sdk-provider.js';
import CONFIG_SCHEMA from '../../../../evals/_schemas/config.schema.json';

/**
 * Every reasoning effort config.schema.json admits, sent to real models of each provider.
 *
 * The unit wire tests show each value reaches the request; these show the vendor takes that
 * request, effort and structured output together, on a current model. The values are read
 * from the schema, so a value added there is sent here too. Which of them a model accepts
 * is the model's own property, so each model case names the values it refuses with an error
 * the caller sees; it answers the rest. A refusal that turns
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

const KEYS = { openai: 'OPENAI_API_KEY', anthropic: 'ANTHROPIC_API_KEY', google: 'GOOGLE_API_KEY' } as const;

/**
 * Each model, its provider's values from the schema, and those it refuses. gpt-6-luna and
 * gpt-5.5 are the models Sentence Structure runs on.
 */
const CASES: ReadonlyArray<{
  type: keyof typeof KEYS;
  model: string;
  efforts: readonly string[];
  refused: readonly string[];
}> = [
  { type: 'openai', model: 'gpt-6-luna', efforts: DEFS.ReasoningEffortOpenAI.enum, refused: ['minimal'] },
  { type: 'openai', model: 'gpt-5.5', efforts: DEFS.ReasoningEffortOpenAI.enum, refused: ['minimal', 'max'] },
  { type: 'anthropic', model: 'claude-haiku-5-5', efforts: DEFS.ReasoningEffortAnthropic.enum, refused: [] },
  { type: 'google', model: 'gemini-3.6-flash', efforts: DEFS.ReasoningEffortGoogle.enum, refused: [] },
];

for (const { type, model, efforts, refused } of CASES) {
  const key = KEYS[type];
  // A refused value the schema no longer lists would never be sent, so it must be one of them.
  for (const value of refused) {
    if (!efforts.includes(value)) {
      throw new Error(`${type}: refused "${value}" is not in config.schema.json's values`);
    }
  }
  const apiKey = process.env[key];
  const run = RUN_INTEGRATION && apiKey ? describe : describe.skip;

  run(`reasoning effort live: ${type} ${model}`, () => {
    for (const effort of efforts) {
      const answers = !refused.includes(effort);
      it(
        `${answers ? 'answers' : 'refuses'} at ${effort}`,
        async () => {
          const provider = createProvider({ type, model, apiKey, maxRetries: 0 });
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
