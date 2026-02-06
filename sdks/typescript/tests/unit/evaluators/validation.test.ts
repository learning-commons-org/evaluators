import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VocabularyEvaluator } from '../../../src/evaluators/vocabulary.js';
import { VALIDATION_LIMITS } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Comprehensive validation tests for input validation
 *
 * Tests the base evaluator validation logic that all evaluators inherit.
 * Uses VocabularyEvaluator as the test subject since it extends BaseEvaluator.
 *
 * All tests use mocked providers to avoid real API calls.
 */

// Mock providers
const createMockProvider = (): LLMProvider => ({
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

// Mock the createProvider factory
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => createMockProvider()),
}));

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => {
  return {
    TelemetryClient: class MockTelemetryClient {
      send = vi.fn().mockResolvedValue(undefined);
    },
  };
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
