import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { z } from 'zod';
import { createProvider } from '../../../src/providers/ai-sdk-provider.js';
import type { ProviderConfig } from '../../../src/providers/base.js';
import { LLMOutputProcessingError } from '../../../src/errors.js';

/**
 * An output cap through the real `ai` package and the real vendor adapters, with only
 * `fetch` replaced: what reaches the wire is what each installed adapter actually sends, and
 * a reply cut off at the limit is reported as each installed adapter actually reports it.
 */

type Vendor = 'openai' | 'anthropic' | 'google';

const SCHEMA = z.object({ score: z.number() });
const MESSAGES = [
  { role: 'system' as const, content: 'You grade things.' },
  { role: 'user' as const, content: 'Grade this.' },
];
const MODELS: Record<Vendor, string> = {
  openai: 'gpt-4.1-2025-04-14',
  anthropic: 'claude-haiku-4-5-20251001',
  google: 'gemini-3.5-flash',
};
const COMPLETE = '{"score": 3}';
const CUT_OFF = '{"score": ';

/** A reply carrying `text`, finished normally or, with `truncated`, at the output limit. */
function reply(vendor: Vendor, text: string, truncated: boolean): unknown {
  switch (vendor) {
    case 'openai':
      return {
        id: 'resp_1',
        object: 'response',
        created_at: 0,
        model: 'm',
        status: truncated ? 'incomplete' : 'completed',
        incomplete_details: truncated ? { reason: 'max_output_tokens' } : null,
        output: [
          {
            type: 'message',
            id: 'msg_1',
            role: 'assistant',
            status: truncated ? 'incomplete' : 'completed',
            content: [{ type: 'output_text', text, annotations: [] }],
          },
        ],
        usage: {
          input_tokens: 11,
          output_tokens: 7,
          input_tokens_details: { cached_tokens: 0 },
          output_tokens_details: { reasoning_tokens: 0 },
        },
      };
    case 'anthropic':
      return {
        id: 'msg_1',
        type: 'message',
        role: 'assistant',
        model: 'm',
        content: [{ type: 'text', text }],
        stop_reason: truncated ? 'max_tokens' : 'end_turn',
        stop_sequence: null,
        usage: { input_tokens: 11, output_tokens: 7 },
      };
    case 'google':
      return {
        candidates: [
          { content: { role: 'model', parts: [{ text }] }, finishReason: truncated ? 'MAX_TOKENS' : 'STOP' },
        ],
        usageMetadata: { promptTokenCount: 11, candidatesTokenCount: 7, totalTokenCount: 18 },
      };
  }
}

/** Where each vendor's request carries the output cap. */
function sentCap(vendor: Vendor, body: Record<string, unknown>): unknown {
  switch (vendor) {
    case 'openai':
      return body.max_output_tokens;
    case 'anthropic':
      return body.max_tokens;
    case 'google':
      return (body.generationConfig as Record<string, unknown> | undefined)?.maxOutputTokens;
  }
}

const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal('fetch', fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

/** The JSON body of the one request the call made. */
function sentBody(): Record<string, unknown> {
  expect(fetchMock).toHaveBeenCalledTimes(1);
  return JSON.parse(fetchMock.mock.calls[0][1].body as string) as Record<string, unknown>;
}

function provider(vendor: Vendor, text = COMPLETE, truncated = false) {
  fetchMock.mockImplementation(async () =>
    new Response(JSON.stringify(reply(vendor, text, truncated)), {
      status: 200,
      headers: { 'content-type': 'application/json' },
    }),
  );
  return createProvider({ type: vendor, model: MODELS[vendor], apiKey: 'fake-key' } satisfies ProviderConfig);
}

describe.each(['openai', 'anthropic', 'google'] as const)('output cap on the wire: %s', (vendor) => {
  const label = `${vendor}:${MODELS[vendor]}`;

  it('sends the cap for a structured call', async () => {
    await provider(vendor).generateStructured({ messages: MESSAGES, schema: SCHEMA, maxTokens: 700 });
    expect(sentCap(vendor, sentBody())).toBe(700);
  });

  it('sends the cap for a text call', async () => {
    await provider(vendor, 'An assumption.').generateText(MESSAGES, 0, { maxTokens: 700 });
    expect(sentCap(vendor, sentBody())).toBe(700);
  });

  it('sends no cap of its own for a text call given none', async () => {
    await provider(vendor, 'An assumption.').generateText(MESSAGES, 0);
    const cap = sentCap(vendor, sentBody());
    // Anthropic requires the field, and its adapter fills in the model's own ceiling.
    if (vendor === 'anthropic') expect(cap).not.toBe(700);
    else expect(cap).toBeUndefined();
  });

  it.each([
    [0, false],
    [0.7, true],
    [null, true],
    [undefined, true],
  ])('reports structured output cut off at the limit as truncated (temperature %s, retryable %s)', async (temperature, retryable) => {
    const call = provider(vendor, CUT_OFF, true).generateStructured({
      messages: MESSAGES,
      schema: SCHEMA,
      temperature,
      maxTokens: 9,
    });
    const error = await call.catch((e: unknown) => e);
    expect(error).toBeInstanceOf(LLMOutputProcessingError);
    expect((error as LLMOutputProcessingError).message).toBe(
      `${label} stopped at max_tokens=9 before its output was complete.`,
    );
    expect((error as LLMOutputProcessingError).retryable).toBe(retryable);
  });

  it('reports a cut-off that happens to parse as truncated too', async () => {
    // The stop signal decides, as in the Python SDK, not whether the text happens to parse.
    const call = provider(vendor, COMPLETE, true).generateStructured({ messages: MESSAGES, schema: SCHEMA });
    await expect(call).rejects.toThrow(`${label} stopped at its output limit before its output was complete.`);
  });

  it.each([
    [0, false],
    [0.7, true],
    [null, true],
  ])('reports prose cut off at the limit as truncated (temperature %s, retryable %s)', async (temperature, retryable) => {
    const call = provider(vendor, 'The text assumes the reader kno', true).generateText(MESSAGES, temperature, {
      maxTokens: 9,
    });
    const error = await call.catch((e: unknown) => e);
    expect(error).toBeInstanceOf(LLMOutputProcessingError);
    expect((error as LLMOutputProcessingError).message).toBe(
      `${label} stopped at max_tokens=9 before its output was complete.`,
    );
    expect((error as LLMOutputProcessingError).retryable).toBe(retryable);
  });

  it('returns prose that finished normally', async () => {
    const response = await provider(vendor, 'Whole.').generateText(MESSAGES, 0, { maxTokens: 9 });
    expect(response.text).toBe('Whole.');
  });
});

describe('a text call without options', () => {
  it('falls back to the configured temperature for retryability', async () => {
    fetchMock.mockImplementation(async () =>
      new Response(JSON.stringify(reply('google', 'Cut', true)), {
        status: 200,
        headers: { 'content-type': 'application/json' },
      }),
    );
    const p = createProvider({ type: 'google', model: MODELS.google, apiKey: 'k', temperature: 0 });
    const error = await p.generateText(MESSAGES).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(LLMOutputProcessingError);
    expect((error as LLMOutputProcessingError).retryable).toBe(false);
    expect((error as LLMOutputProcessingError).message).toContain('its output limit');
  });
});
