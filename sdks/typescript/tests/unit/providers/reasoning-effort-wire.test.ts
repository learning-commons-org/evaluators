import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod';
import { VERSION as OPENAI_ADAPTER_VERSION } from '@ai-sdk/openai';
import { ConfigurationError } from '../../../src/errors.js';
import { OPENAI_MAX_EFFORT_SINCE, createProvider } from '../../../src/providers/ai-sdk-provider.js';
import type { ProviderConfig, ReasoningEffort } from '../../../src/providers/base.js';

/**
 * A reasoning effort through the real `ai` package and the real vendor adapters, with only
 * `fetch` replaced: what reaches the wire is what each installed adapter actually sends.
 * The values are config.schema.json's per-provider lists.
 */

const SCHEMA = z.object({ score: z.number() });
const MESSAGES = [
  { role: 'system' as const, content: 'You grade things.' },
  { role: 'user' as const, content: 'Grade this.' },
];

const OPENAI_EFFORTS: ReasoningEffort[] = ['none', 'minimal', 'low', 'medium', 'high', 'xhigh', 'max'];
const ANTHROPIC_EFFORTS: ReasoningEffort[] = ['low', 'medium', 'high', 'xhigh', 'max'];
const GOOGLE_EFFORTS: ReasoningEffort[] = ['minimal', 'low', 'medium', 'high'];

const TEXT = '{"score": 3}';
const REPLIES: Record<'openai' | 'anthropic' | 'google', unknown> = {
  openai: {
    id: 'resp_1',
    object: 'response',
    created_at: 0,
    model: 'm',
    status: 'completed',
    output: [
      {
        type: 'message',
        id: 'msg_1',
        role: 'assistant',
        status: 'completed',
        content: [{ type: 'output_text', text: TEXT, annotations: [] }],
      },
    ],
    usage: {
      input_tokens: 11,
      output_tokens: 7,
      input_tokens_details: { cached_tokens: 0 },
      output_tokens_details: { reasoning_tokens: 0 },
    },
  },
  anthropic: {
    id: 'msg_1',
    type: 'message',
    role: 'assistant',
    model: 'm',
    // An adapter that does not know the model's native structured output asks for it
    // through a `json` tool instead, so the reply answers both ways.
    content: [
      { type: 'text', text: TEXT },
      { type: 'tool_use', id: 'toolu_1', name: 'json', input: { score: 3 } },
    ],
    stop_reason: 'end_turn',
    stop_sequence: null,
    usage: { input_tokens: 11, output_tokens: 7 },
  },
  google: {
    candidates: [{ content: { role: 'model', parts: [{ text: TEXT }] }, finishReason: 'STOP' }],
    usageMetadata: { promptTokenCount: 11, candidatesTokenCount: 7, totalTokenCount: 18 },
  },
};

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** Whether the installed `@ai-sdk/openai` can send `max`, by its numeric release parts. */
const OPENAI_SENDS_MAX = ((v: string, min: string) => {
  const [a, b] = [v, min].map((x) => x.split('.').map(Number));
  return a[0] !== b[0] ? a[0] > b[0] : a[1] !== b[1] ? a[1] > b[1] : a[2] >= b[2];
})(OPENAI_ADAPTER_VERSION, OPENAI_MAX_EFFORT_SINCE);

/** The JSON body of the one request the call made. */
function sentBody(): Record<string, unknown> {
  expect(fetchMock).toHaveBeenCalledTimes(1);
  return JSON.parse(fetchMock.mock.calls[0][1].body as string) as Record<string, unknown>;
}

function provider(type: 'openai' | 'anthropic' | 'google', model: string) {
  fetchMock.mockImplementation(async () =>
    new Response(JSON.stringify(REPLIES[type]), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
  return createProvider({ type, model, apiKey: 'fake-key' } satisfies ProviderConfig);
}

describe('reasoning effort on the wire', () => {
  describe('openai', () => {
    // The models Sentence Structure runs on, and a released reasoning model.
    for (const model of ['gpt-5.5', 'gpt-6-luna']) {
      it.each(OPENAI_EFFORTS)(`${model}: sends %s as reasoning.effort and nothing else`, async (effort) => {
        const call = provider('openai', model).generateStructured({ messages: MESSAGES, schema: SCHEMA, reasoningEffort: effort });
        // Below OPENAI_MAX_EFFORT_SINCE the adapter rejects `max`; the SDK says so first.
        if (effort === 'max' && !OPENAI_SENDS_MAX) {
          await expect(call).rejects.toThrow(ConfigurationError);
          expect(fetchMock).not.toHaveBeenCalled();
          return;
        }
        await call;
        expect(sentBody().reasoning).toEqual({ effort });
      });
    }

    it('sends no reasoning when no effort is given', async () => {
      await provider('openai', 'gpt-5.5').generateStructured({ messages: MESSAGES, schema: SCHEMA });
      expect(sentBody()).not.toHaveProperty('reasoning');
    });
  });

  describe('anthropic', () => {
    it.each(ANTHROPIC_EFFORTS)('sends %s as output_config.effort', async (effort) => {
      await provider('anthropic', 'claude-opus-5-5').generateStructured({ messages: MESSAGES, schema: SCHEMA, reasoningEffort: effort });
      const body = sentBody();
      const outputConfig = body.output_config as Record<string, unknown>;
      expect(outputConfig.effort).toBe(effort);
      // In native structured-output mode the format shares output_config with the effort;
      // in the `json`-tool mode it travels as the tool instead.
      if (!body.tools) expect(outputConfig).toHaveProperty('format');
    });

    it('sends no effort when none is given', async () => {
      await provider('anthropic', 'claude-opus-5-5').generateStructured({ messages: MESSAGES, schema: SCHEMA });
      expect((sentBody().output_config as Record<string, unknown> | undefined)?.effort).toBeUndefined();
    });
  });

  describe('google', () => {
    it.each(GOOGLE_EFFORTS)('sends %s as generationConfig.thinkingConfig.thinkingLevel', async (effort) => {
      await provider('google', 'gemini-3.5-flash').generateStructured({ messages: MESSAGES, schema: SCHEMA, reasoningEffort: effort });
      const config = sentBody().generationConfig as Record<string, unknown>;
      expect(config.thinkingConfig).toEqual({ thinkingLevel: effort });
    });

    it('sends no thinking config when no effort is given', async () => {
      await provider('google', 'gemini-3.5-flash').generateStructured({ messages: MESSAGES, schema: SCHEMA });
      expect(sentBody().generationConfig).not.toHaveProperty('thinkingConfig');
    });
  });
});
