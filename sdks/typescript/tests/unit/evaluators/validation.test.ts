import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VocabularyEvaluator } from '../../../src/evaluators/vocabulary.js';
import { SmkEvaluator } from '../../../src/evaluators/smk.js';
import { VALIDATION_LIMITS, Provider, BaseEvaluator } from '../../../src/evaluators/base.js';
import { ConfigurationError, InputValidationError } from '../../../src/errors.js';
import type { LLMProvider } from '../../../src/providers/base.js';
import { createProvider } from '../../../src/providers/index.js';

/**
 * Comprehensive validation tests for input validation
 *
 * Tests the base evaluator validation logic that all evaluators inherit.
 * Uses VocabularyEvaluator as the test subject since it extends BaseEvaluator.
 *
 * All tests use mocked providers to avoid real API calls.
 */

// Mock providers
const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

// Mock the createProvider factory
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn((config) => createMockProvider(config)),
}));

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => {
  return {
    TelemetryClient: class MockTelemetryClient {
      send = vi.fn().mockResolvedValue(undefined);
    },
  };
});

describe('Configuration Validation', () => {
  it('should throw ConfigurationError when googleApiKey is missing', () => {
    expect(() => new VocabularyEvaluator({
      googleApiKey: '',
      openaiApiKey: 'test-openai-key',
    })).toThrow(ConfigurationError);
  });

  it('should throw ConfigurationError when openaiApiKey is missing', () => {
    expect(() => new VocabularyEvaluator({
      googleApiKey: 'test-google-key',
      openaiApiKey: '',
    })).toThrow(ConfigurationError);
  });
});

describe('ModelOverride', () => {
  it('should bypass default key validation when modelOverride is provided with the matching key', () => {
    // No googleApiKey or openaiApiKey — normally would throw for VocabularyEvaluator
    expect(() => new VocabularyEvaluator({
      anthropicApiKey: 'test-key',
      modelOverride: { provider: Provider.Anthropic, model: 'claude-sonnet-4-6' },
    })).not.toThrow();
  });

  it('should throw ConfigurationError when the override provider key is missing', () => {
    // modelOverride requests Anthropic but no anthropicApiKey provided
    expect(() => new VocabularyEvaluator({
      modelOverride: { provider: Provider.Anthropic, model: 'claude-sonnet-4-6' },
    })).toThrow(ConfigurationError);
  });

  it('should pass override params to createProvider', () => {
    vi.mocked(createProvider).mockClear();

    new SmkEvaluator({
      anthropicApiKey: 'test-key',
      modelOverride: { provider: Provider.Anthropic, model: 'claude-haiku-4-5-20251001' },
      telemetry: false,
    });

    expect(vi.mocked(createProvider)).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'anthropic', model: 'claude-haiku-4-5-20251001' })
    );
  });

  it('should not call createProvider with default provider params when override is set', () => {
    vi.mocked(createProvider).mockClear();

    new SmkEvaluator({
      openaiApiKey: 'test-key',
      modelOverride: { provider: Provider.OpenAI, model: 'gpt-4o-mini' },
      telemetry: false,
    });

    expect(vi.mocked(createProvider)).toHaveBeenCalledWith(
      expect.objectContaining({ type: 'openai', model: 'gpt-4o-mini' })
    );
    expect(vi.mocked(createProvider)).not.toHaveBeenCalledWith(
      expect.objectContaining({ type: 'google' })
    );
  });

  describe('modelOverride shape validation', () => {
    it('should throw ConfigurationError when model is an empty string', () => {
      expect(() => new SmkEvaluator({
        openaiApiKey: 'test-key',
        modelOverride: { provider: Provider.OpenAI, model: '' },
        telemetry: false,
      })).toThrow(ConfigurationError);
    });

    it('should throw ConfigurationError when model is whitespace only', () => {
      expect(() => new SmkEvaluator({
        openaiApiKey: 'test-key',
        modelOverride: { provider: Provider.OpenAI, model: '   ' },
        telemetry: false,
      })).toThrow(ConfigurationError);
    });

    it('should throw ConfigurationError when provider is not a valid Provider value', () => {
      expect(() => new SmkEvaluator({
        openaiApiKey: 'test-key',
        // @ts-expect-error intentional invalid provider for runtime test
        modelOverride: { provider: 'unsupported-provider', model: 'some-model' },
        telemetry: false,
      })).toThrow(ConfigurationError);
    });

    it('error message should list valid providers when provider is invalid', () => {
      expect(() => new SmkEvaluator({
        openaiApiKey: 'test-key',
        // @ts-expect-error intentional invalid provider for runtime test
        modelOverride: { provider: 'unsupported-provider', model: 'some-model' },
        telemetry: false,
      })).toThrow(/openai.*google.*anthropic|anthropic.*openai.*google/i);
    });

  });

  describe('model-not-found runtime error', () => {
    it('should throw ConfigurationError when provider returns a 404 for the model', async () => {
      vi.mocked(createProvider).mockReturnValueOnce(
        createMockProvider({ type: 'openai', model: 'gpt-fake' })
      );

      const evaluator = new SmkEvaluator({
        openaiApiKey: 'test-key',
        modelOverride: { provider: Provider.OpenAI, model: 'gpt-fake' },
        telemetry: false,
      });

      const notFoundError = Object.assign(
        new Error("The model 'gpt-fake' does not exist"),
        { statusCode: 404 }
      );
      // @ts-expect-error accessing private field for test
      vi.mocked(evaluator.provider.generateStructured).mockRejectedValueOnce(notFoundError);

      await expect(
        evaluator.evaluate('This is a sample text long enough to pass validation.', '5')
      ).rejects.toThrow(ConfigurationError);
    });
  });
});

describe('Input Validation - Text Validation', () => {
  let evaluator: VocabularyEvaluator;

  beforeEach(() => {
    vi.clearAllMocks();

    evaluator = new VocabularyEvaluator({
      googleApiKey: 'test-google-key',
      openaiApiKey: 'test-openai-key',
      telemetry: false,
    });
  });

  describe('Empty text validation', () => {
    it.each([
      ['empty string', ''],
      ['spaces only', '   '],
      ['tabs only', '\t\t\t'],
      ['newlines only', '\n\n\n'],
      ['mixed whitespace', '  \t\n  '],
    ])('should reject %s', async (_label, text) => {
      await expect(evaluator.evaluate(text, '5'))
        .rejects.toThrow('Text cannot be empty or contain only whitespace');
    });
  });

  describe('Minimum length validation', () => {
    // The SDK minimum excludes empty input only, so short-but-real text is no
    // longer a validation failure. Meaningful minimums are declared in each
    // evaluator's input schema.
    it('does not reject short text as invalid input', async () => {
      const error = await evaluator.evaluate('Hello wo', '5').catch((e) => e);
      expect(error).not.toBeInstanceOf(InputValidationError);
    });
  });

  describe('Maximum length validation', () => {
    it(`should reject text longer than ${VALIDATION_LIMITS.MAX_TEXT_LENGTH.toLocaleString()} characters`, async () => {
      const longText = 'a'.repeat(VALIDATION_LIMITS.MAX_TEXT_LENGTH + 1);

      await expect(evaluator.evaluate(longText, '5'))
        .rejects.toThrow(new RegExp(`Text is too long\\. Maximum length is ${VALIDATION_LIMITS.MAX_TEXT_LENGTH.toLocaleString()} characters, received ${(VALIDATION_LIMITS.MAX_TEXT_LENGTH + 1).toLocaleString()} characters`));
    });
  });
});

describe('Input Validation - Grade Validation', () => {
  let evaluator: VocabularyEvaluator;

  beforeEach(() => {
    vi.clearAllMocks();

    evaluator = new VocabularyEvaluator({
      googleApiKey: 'test-google-key',
      openaiApiKey: 'test-openai-key',
      telemetry: false,
    });
  });

  describe('Valid grade range', () => {
    it.each([
      ['K', 'K'],
      ['1', '1'],
      ['2', '2'],
    ])('should reject grade %s (below minimum)', async (_label, grade) => {
      const validText = 'This is a sample text for testing.';

      await expect(evaluator.evaluate(validText, grade))
        .rejects.toThrow(`Invalid grade "${grade}". Supported grades for this evaluator: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12`);
    });

    it.each([
      ['13', '13'],
      ['99', '99'],
    ])('should reject grade %s (above maximum)', async (_label, grade) => {
      const validText = 'This is a sample text for testing.';

      await expect(evaluator.evaluate(validText, grade))
        .rejects.toThrow(`Invalid grade "${grade}". Supported grades for this evaluator: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12`);
    });

    it.each([
      ['invalid', 'invalid'],
      ['grade5', 'grade5'],
      ['empty string', ''],
    ])('should reject grade %s (invalid format)', async (_label, grade) => {
      const validText = 'This is a sample text for testing.';

      await expect(evaluator.evaluate(validText, grade))
        .rejects.toThrow(`Invalid grade "${grade}". Supported grades for this evaluator: 3, 4, 5, 6, 7, 8, 9, 10, 11, 12`);
    });
  });
});

describe('providerContext — dependency attribution', () => {
  // Exposed via a minimal subclass because providerContext is protected.
  class Probe extends BaseEvaluator {
    static readonly metadata = {
      id: 'probe',
      name: 'Probe',
      description: 'test seam',
      supportedGrades: ['3'] as const,
      defaultProviders: [Provider.Google] as const,
    };
    contextFor(label: string) {
      return this.providerContext({
        label,
        generateStructured: vi.fn(),
        generateText: vi.fn(),
      });
    }
  }

  const probe = () =>
    new Probe({ googleApiKey: 'k', telemetry: false });

  it.each([
    ['openai:gpt-4o-2024-11-20', 'openai', 'gpt-4o-2024-11-20'],
    ['google:gemini-3-flash-preview', 'google', 'gemini-3-flash-preview'],
    ['anthropic:claude-opus-5', 'anthropic', 'claude-opus-5'],
  ])('names the vendor for %s and strips it from model', (label, dependency, model) => {
    expect(probe().contextFor(label)).toEqual({ dependency, model });
  });

  // A modelOverride resolves to one of our vendors, so it is still nameable —
  // overriding does not make a call "custom".
  it('reports the overridden vendor, not custom', () => {
    expect(probe().contextFor('anthropic:claude-haiku-4-5-20251001')).toEqual({
      dependency: 'anthropic',
      model: 'claude-haiku-4-5-20251001',
    });
  });

  // An injected llmProvider labels itself; the vendor is the caller's to know.
  it.each([
    ['azure:gpt-4o', 'azure:gpt-4o'],
    ['bedrock:anthropic.claude-v2', 'bedrock:anthropic.claude-v2'],
    ['my-gateway', 'my-gateway'],
  ])('reports custom for the unrecognised label %s, keeping it as model', (label, model) => {
    expect(probe().contextFor(label)).toEqual({ dependency: 'custom', model });
  });

  it('does not let a vendor name appear anywhere in the label pass as that vendor', () => {
    // Only the prefix counts — a model id mentioning a vendor must not win.
    expect(probe().contextFor('gateway:openai-compatible')).toEqual({
      dependency: 'custom',
      model: 'gateway:openai-compatible',
    });
  });

  // A label carrying no model id still names the vendor where it can, and never
  // reports an empty model — a blank attribution is worse than a redundant one.
  it.each([
    ['openai', 'openai', 'openai'],
    ['openai:', 'openai', 'openai:'],
  ])('keeps %s whole as model when it carries no model id', (label, dependency, model) => {
    expect(probe().contextFor(label)).toEqual({ dependency, model });
  });

  it.each([
    ['the empty label', ''],
    ['a label with no prefix', ':gpt-4o'],
    // Prefix matching is exact: a differently-cased vendor is not our vendor.
    ['a differently-cased vendor', 'OpenAI:gpt-4o'],
  ])('reports custom for %s', (_why, label) => {
    expect(probe().contextFor(label)).toEqual({ dependency: 'custom', model: label });
  });

  // Binds attribution to the label VercelAIProvider actually emits. Without it
  // every case here is hand-written, so a label-format change would reroute all
  // real traffic to `custom` with the suite still green.
  it('names the vendor for a label a real provider emits', () => {
    const provider = createProvider({
      type: 'openai',
      model: 'gpt-4o-2024-11-20',
      apiKey: 'k',
    });
    expect(probe().contextFor(provider.label)).toEqual({
      dependency: 'openai',
      model: 'gpt-4o-2024-11-20',
    });
  });
});
