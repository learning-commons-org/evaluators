import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VocabularyEvaluator } from '../../../src/evaluators/vocabulary.js';
import { SmkEvaluator } from '../../../src/evaluators/smk.js';
import { VALIDATION_LIMITS, Provider } from '../../../src/evaluators/base.js';
import { ConfigurationError } from '../../../src/errors.js';
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
    it(`should reject text shorter than ${VALIDATION_LIMITS.MIN_TEXT_LENGTH} characters`, async () => {
      const shortText = 'Hello wo'; // 8 chars after trim
      await expect(evaluator.evaluate(shortText, '5'))
        .rejects.toThrow(`Text is too short. Minimum length is ${VALIDATION_LIMITS.MIN_TEXT_LENGTH} characters, received 8 characters`);
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
