import { describe, it, expect, vi, beforeEach } from 'vitest';
import { z } from 'zod';

/**
 * A request may carry image attachments. These tests pin how the provider hands them to the
 * AI SDK: text-only requests unchanged; attachments placed on the final user turn before or
 * after its text, as each one's `position` says, as `{ type: 'file', data, mediaType }` parts (the SDK's `image` part is
 * deprecated); earlier turns untouched.
 */

const generateText = vi.fn().mockResolvedValue({
  text: 'ok',
  output: { ok: true },
  usage: { inputTokens: 1, outputTokens: 1 },
});

vi.mock('ai', () => ({ generateText, Output: { object: vi.fn((cfg) => cfg) } }));
vi.mock('@ai-sdk/google', () => ({ createGoogleGenerativeAI: vi.fn(() => vi.fn((m: string) => ({ m }))) }));

const PNG = Uint8Array.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const SCHEMA = z.object({ ok: z.boolean() });

describe('VercelAIProvider with attachments', () => {
  beforeEach(() => generateText.mockClear());

  async function provider() {
    const { createProvider } = await import('../../../src/providers/ai-sdk-provider.js');
    return createProvider({ type: 'google', model: 'gemini-3.6-flash', apiKey: 'k' });
  }

  it('declares attachment support', async () => {
    expect((await provider()).supportsAttachments).toBe(true);
  });

  it('places attachments on the last user turn, ahead of its text, as file parts', async () => {
    const p = await provider();
    await p.generateStructured({
      messages: [
        { role: 'system', content: 'You are a reviewer.' },
        { role: 'user', content: 'Claim: five ladybirds.' },
      ],
      schema: SCHEMA,
      attachments: [{ type: 'image', data: PNG, mediaType: 'image/png', position: 'before_text' }],
    });
    const call = generateText.mock.calls[0][0];
    expect(call.system).toBe('You are a reviewer.');
    expect(call.messages).toEqual([
      {
        role: 'user',
        content: [
          { type: 'file', data: PNG, mediaType: 'image/png' },
          { type: 'text', text: 'Claim: five ladybirds.' },
        ],
      },
    ]);
  });

  it('places each attachment before or after the text as its position says, keeping array order', async () => {
    const JPEG = Uint8Array.from([0xff, 0xd8, 0xff, 0xe0]);
    const WEBP = Uint8Array.from([0x52, 0x49, 0x46, 0x46]);
    const p = await provider();
    await p.generateStructured({
      messages: [{ role: 'user', content: 'Passage.' }],
      schema: SCHEMA,
      attachments: [
        { type: 'image', data: PNG, mediaType: 'image/png', position: 'after_text' },
        { type: 'image', data: JPEG, mediaType: 'image/jpeg', position: 'before_text' },
        { type: 'image', data: WEBP, mediaType: 'image/webp', position: 'after_text' },
      ],
    });
    expect(generateText.mock.calls[0][0].messages[0].content).toEqual([
      { type: 'file', data: JPEG, mediaType: 'image/jpeg' },
      { type: 'text', text: 'Passage.' },
      { type: 'file', data: PNG, mediaType: 'image/png' },
      { type: 'file', data: WEBP, mediaType: 'image/webp' },
    ]);
  });

  it('leaves earlier turns alone when attaching to the last user turn', async () => {
    const p = await provider();
    await p.generateStructured({
      messages: [
        { role: 'user', content: 'first' },
        { role: 'assistant', content: 'reply' },
        { role: 'user', content: 'second' },
      ],
      schema: SCHEMA,
      attachments: [{ type: 'image', data: PNG, mediaType: 'image/png', position: 'before_text' }],
    });
    const { messages } = generateText.mock.calls[0][0];
    expect(messages[0]).toEqual({ role: 'user', content: 'first' });
    expect(messages[1]).toEqual({ role: 'assistant', content: 'reply' });
    expect(messages[2].content[1]).toEqual({ type: 'text', text: 'second' });
  });

  it('sends text-only requests exactly as before', async () => {
    const p = await provider();
    await p.generateStructured({ messages: [{ role: 'system', content: 'sys' }, { role: 'user', content: 'hello' }], schema: SCHEMA });
    const call = generateText.mock.calls[0][0];
    expect(call.system).toBe('sys');
    expect(call.messages).toEqual([{ role: 'user', content: 'hello' }]);
  });

  it('refuses attachments when there is no user turn to carry them', async () => {
    const p = await provider();
    await expect(
      p.generateStructured({ messages: [{ role: 'system', content: 'sys' }], schema: SCHEMA, attachments: [{ type: 'image', data: PNG, mediaType: 'image/png', position: 'before_text' }] }),
    ).rejects.toThrow(/need a user message/);
  });
});
