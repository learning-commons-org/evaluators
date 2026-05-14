import { describe, it, expect } from 'vitest';
import { runPreprocessingStep } from '../../../src/features/preprocessing.js';

const SAMPLE_TEXT = 'The cat sat on the mat. The dog ran away.';

describe('runPreprocessingStep', () => {
  describe('text-readability library', () => {
    it('calls the specified function and applies round post_transform', () => {
      const result = runPreprocessingStep(SAMPLE_TEXT, {
        library: 'text-readability',
        function: 'fleschKincaidGrade',
        post_transform: { type: 'round', precision: 2 },
      });

      expect(typeof result).toBe('number');
      // Result should have at most 2 decimal places after rounding
      expect(result).toBe(Math.round(result * 100) / 100);
    });

    it('returns raw value when no post_transform is specified', () => {
      const result = runPreprocessingStep(SAMPLE_TEXT, {
        library: 'text-readability',
        function: 'fleschKincaidGrade',
      });

      expect(typeof result).toBe('number');
    });

    it('throws for an unknown function name within text-readability', () => {
      expect(() =>
        runPreprocessingStep(SAMPLE_TEXT, {
          library: 'text-readability',
          function: 'nonExistentFn',
        }),
      ).toThrow('Function "nonExistentFn" not found in text-readability.');
    });
  });

  describe('error handling', () => {
    it('throws for an unsupported library and lists supported ones', () => {
      expect(() =>
        runPreprocessingStep(SAMPLE_TEXT, {
          library: 'unknown-lib',
          function: 'someFunction',
        }),
      ).toThrow(/Unsupported preprocessing library "unknown-lib"\. Supported: .+/);
    });

    it('throws for an unsupported post_transform type and lists supported ones', () => {
      expect(() =>
        runPreprocessingStep(SAMPLE_TEXT, {
          library: 'text-readability',
          function: 'fleschKincaidGrade',
          post_transform: { type: 'floor' },
        }),
      ).toThrow(/Unsupported post_transform type "floor"\. Supported: .+/);
    });
  });

  describe('round post_transform precision', () => {
    it('respects precision: 0 (integer rounding)', () => {
      const result = runPreprocessingStep(SAMPLE_TEXT, {
        library: 'text-readability',
        function: 'fleschKincaidGrade',
        post_transform: { type: 'round', precision: 0 },
      });

      expect(result).toBe(Math.round(result));
    });

    it('uses precision 0 as default when precision is omitted', () => {
      const withDefault = runPreprocessingStep(SAMPLE_TEXT, {
        library: 'text-readability',
        function: 'fleschKincaidGrade',
        post_transform: { type: 'round' },
      });

      expect(withDefault).toBe(Math.round(withDefault));
    });
  });
});
