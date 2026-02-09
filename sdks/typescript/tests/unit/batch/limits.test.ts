import { describe, it, expect } from 'vitest';
import { getAvailableGroups, BatchEvaluator } from '../../../src/batch/index.js';
import type { BatchInput } from '../../../src/batch/index.js';

function makeInputs(count: number): BatchInput[] {
  return Array.from({ length: count }, (_, i) => ({
    text: 'The cat sat on the mat.',
    grade: '3',
    rowIndex: i + 2,
    originalRow: { text: 'The cat sat on the mat.', grade: '3' },
  }));
}

describe('getAvailableGroups', () => {
  it('returns at least one group', () => {
    expect(getAvailableGroups().length).toBeGreaterThan(0);
  });

  it('includes the text-complexity group', () => {
    const ids = getAvailableGroups().map((g) => g.id);
    expect(ids).toContain('text-complexity');
  });

  it('each group has required metadata fields', () => {
    for (const g of getAvailableGroups()) {
      expect(g.id).toBeTruthy();
      expect(g.name).toBeTruthy();
      expect(g.description).toBeTruthy();
      expect(Array.isArray(g.evaluatorIds)).toBe(true);
      expect(g.evaluatorIds.length).toBeGreaterThan(0);
      expect(typeof g.requiresGoogleKey).toBe('boolean');
      expect(typeof g.requiresOpenAIKey).toBe('boolean');
      expect(typeof g.maxInputRows).toBe('number');
      expect(g.maxInputRows).toBeGreaterThan(0);
    }
  });

  it('text-complexity group contains vocabulary, sentence-structure, and grade-level-appropriateness', () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    expect(group.evaluatorIds).toContain('vocabulary');
    expect(group.evaluatorIds).toContain('sentence-structure');
    expect(group.evaluatorIds).toContain('grade-level-appropriateness');
  });

  it('text-complexity group requires both Google and OpenAI keys', () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    expect(group.requiresGoogleKey).toBe(true);
    expect(group.requiresOpenAIKey).toBe(true);
  });

  it('text-complexity group enforces a row limit of 100', () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    expect(group.maxInputRows).toBe(100);
  });
});

describe('BatchEvaluator.evaluate() — input validation', () => {
  const evaluator = new BatchEvaluator({
    googleApiKey: 'fake-google-key',
    openaiApiKey: 'fake-openai-key',
  });

  it('throws for an unknown groupId before any evaluator is initialised', async () => {
    await expect(evaluator.evaluate(makeInputs(1), 'nonexistent-group'))
      .rejects.toThrow('Unknown evaluator group: "nonexistent-group"');
  });

  it('throws when input row count exceeds the group maxInputRows', async () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const tooMany = makeInputs(group.maxInputRows + 1);

    await expect(evaluator.evaluate(tooMany, group.id))
      .rejects.toThrow(`Input exceeds limit for "${group.id}"`);
  });

  it('cancel() before evaluation starts returns an empty array', () => {
    const fresh = new BatchEvaluator({ googleApiKey: 'k', openaiApiKey: 'k' });
    expect(fresh.cancel()).toEqual([]);
  });
});
