import { describe, it, expect, vi, afterEach } from 'vitest';
import { z } from 'zod';
import type { ProviderConfig } from '../../../src/providers/base.js';

/**
 * Unit tests for VercelAIProvider / createProvider.
 *
 * The provider lazily `import()`s the vendor adapter (`@ai-sdk/openai`,
 * `@ai-sdk/anthropic`, `@ai-sdk/google`) so consumers only install what they use.
 * These tests mock `ai` and the adapters so we can exercise `getModel()` for each
 * provider type — including the "adapter not installed" path — without real keys.
 *
 * Each test loads a fresh copy of the module via `vi.resetModules()` + `vi.doMock`
 * so it can independently decide which adapter imports succeed or fail.
 */

type AdapterName = 'openai' | 'anthropic' | 'google';

const buildModel = (provider: string) =>
  vi.fn((model: string) => ({ provider, model }));

async function loadProvider(opts: { failImports?: AdapterName[] } = {}) {
  vi.resetModules();

  const generateText = vi.fn().mockResolvedValue({
    text: 'generated text',
    output: { ok: true },
    usage: { inputTokens: 10, outputTokens: 5 },
  });
  vi.doMock('ai', () => ({
    generateText,
    Output: { object: vi.fn((cfg) => cfg) },
  }));

  const createOpenAI = vi.fn(() => buildModel('openai'));
  const createAnthropic = vi.fn(() => buildModel('anthropic'));
  const createGoogleGenerativeAI = vi.fn(() => buildModel('google'));

  const fails = (name: AdapterName) => opts.failImports?.includes(name) ?? false;

  if (fails('openai')) {
    vi.doMock('@ai-sdk/openai', () => { throw new Error('Cannot find module'); });
  } else {
    vi.doMock('@ai-sdk/openai', () => ({ createOpenAI }));
  }

  if (fails('anthropic')) {
    vi.doMock('@ai-sdk/anthropic', () => { throw new Error('Cannot find module'); });
  } else {
    vi.doMock('@ai-sdk/anthropic', () => ({ createAnthropic }));
  }

  if (fails('google')) {
    vi.doMock('@ai-sdk/google', () => { throw new Error('Cannot find module'); });
  } else {
    vi.doMock('@ai-sdk/google', () => ({ createGoogleGenerativeAI }));
  }

  const mod = await import('../../../src/providers/ai-sdk-provider.js');
  return { mod, generateText, createOpenAI, createAnthropic, createGoogleGenerativeAI };
}

afterEach(() => {
  vi.resetModules();
  vi.clearAllMocks();
});

describe('VercelAIProvider - constructor validation', () => {
  it('rejects the custom type (custom providers bypass this class)', async () => {
    const { mod } = await loadProvider();
    expect(() => new mod.VercelAIProvider({ type: 'custom', model: 'x' }))
      .toThrow('VercelAIProvider does not support custom type');
  });

  it('requires a non-empty model', async () => {
    const { mod } = await loadProvider();
    expect(() => new mod.VercelAIProvider({ type: 'openai', model: '' }))
      .toThrow('model is required');
    expect(() => new mod.VercelAIProvider({ type: 'openai', model: '   ' }))
      .toThrow('model is required');
  });

  it('exposes a "type:model" label', async () => {
    const { mod } = await loadProvider();
    const provider = new mod.VercelAIProvider({ type: 'openai', model: 'gpt-4o-mini' });
    expect(provider.label).toBe('openai:gpt-4o-mini');
  });
});

describe('VercelAIProvider - getModel adapter resolution', () => {
  const cases: Array<{ type: ProviderConfig['type']; factory: string }> = [
    { type: 'openai', factory: 'createOpenAI' },
    { type: 'anthropic', factory: 'createAnthropic' },
    { type: 'google', factory: 'createGoogleGenerativeAI' },
  ];

  for (const { type, factory } of cases) {
    it(`loads the ${type} adapter and passes the api key`, async () => {
      const ctx = await loadProvider();
      const provider = new ctx.mod.VercelAIProvider({ type, model: 'model-x', apiKey: 'secret' });

      const res = await provider.generateText([{ role: 'user', content: 'hi' }]);

      expect(res.text).toBe('generated text');
      expect(res.usage).toEqual({ inputTokens: 10, outputTokens: 5 });
      // The matching adapter factory was called with the api key, then with the model id.
      const created = ctx[factory as keyof typeof ctx] as ReturnType<typeof vi.fn>;
      expect(created).toHaveBeenCalledWith({ apiKey: 'secret' });
      expect(created.mock.results[0].value).toHaveBeenCalledWith('model-x');
    });
  }

  it('omits api key options when no key is provided', async () => {
    const ctx = await loadProvider();
    const provider = new ctx.mod.VercelAIProvider({ type: 'openai', model: 'model-x' });

    await provider.generateText([{ role: 'user', content: 'hi' }]);

    expect(ctx.createOpenAI).toHaveBeenCalledWith({});
  });

  it('throws a helpful error when the selected adapter is not installed', async () => {
    const ctx = await loadProvider({ failImports: ['anthropic'] });
    const provider = new ctx.mod.VercelAIProvider({ type: 'anthropic', model: 'claude-x' });

    await expect(provider.generateText([{ role: 'user', content: 'hi' }]))
      .rejects.toThrow('To use the Anthropic provider, install its adapter: npm install @ai-sdk/anthropic');
  });

  it('throws a helpful error for each adapter when missing', async () => {
    for (const [type, name, pkg] of [
      ['openai', 'OpenAI', '@ai-sdk/openai'],
      ['google', 'Google', '@ai-sdk/google'],
    ] as const) {
      const ctx = await loadProvider({ failImports: [type] });
      const provider = new ctx.mod.VercelAIProvider({ type, model: 'm' });
      await expect(provider.generateText([{ role: 'user', content: 'hi' }]))
        .rejects.toThrow(`To use the ${name} provider, install its adapter: npm install ${pkg}`);
    }
  });

  it('throws on an unsupported provider type', async () => {
    const ctx = await loadProvider();
    // Bypass the constructor's type union to reach the switch default.
    const provider = new ctx.mod.VercelAIProvider({ type: 'cohere' as never, model: 'm' });
    await expect(provider.generateText([{ role: 'user', content: 'hi' }]))
      .rejects.toThrow('Unsupported provider type: cohere');
  });
});

describe('VercelAIProvider - generateStructured', () => {
  it('returns structured output and usage from the adapter', async () => {
    const ctx = await loadProvider();
    const provider = new ctx.mod.VercelAIProvider({ type: 'openai', model: 'gpt-4o-mini' });

    const res = await provider.generateStructured({
      messages: [{ role: 'user', content: 'hi' }],
      schema: z.object({ ok: z.boolean() }),
    });

    expect(res.data).toEqual({ ok: true });
    expect(res.model).toBe('gpt-4o-mini');
    expect(res.usage).toEqual({ inputTokens: 10, outputTokens: 5 });
  });
});

describe('createProvider', () => {
  it('returns the custom provider instance when type is custom', async () => {
    const { mod } = await loadProvider();
    const customProvider = {
      label: 'custom:thing',
      generateStructured: vi.fn(),
      generateText: vi.fn(),
    };
    const provider = mod.createProvider({ type: 'custom', customProvider });
    expect(provider).toBe(customProvider);
  });

  it('returns a VercelAIProvider for vendor types', async () => {
    const { mod } = await loadProvider();
    const provider = mod.createProvider({ type: 'openai', model: 'gpt-4o-mini' });
    expect(provider).toBeInstanceOf(mod.VercelAIProvider);
  });
});

describe('VercelAIProvider - maxTokens', () => {
  const CONFIG: ProviderConfig = { type: 'openai', model: 'gpt-4o-mini', apiKey: 'k' };
  const schema = z.object({ ok: z.boolean() });
  const messages = [{ role: 'user' as const, content: 'hi' }];

  it('forwards maxTokens under the vendor name the SDK actually reads', async () => {
    const { mod, generateText } = await loadProvider();
    await new mod.VercelAIProvider(CONFIG).generateStructured({ messages, schema, maxTokens: 4096 });

    const call = generateText.mock.calls[0][0];
    expect(call.maxOutputTokens).toBe(4096);
    expect(call).not.toHaveProperty('maxTokens');
  });

  it('omits it entirely when unset', async () => {
    const { mod, generateText } = await loadProvider();
    await new mod.VercelAIProvider(CONFIG).generateStructured({ messages, schema });

    expect(generateText.mock.calls[0][0]).not.toHaveProperty('maxOutputTokens');
  });
});
