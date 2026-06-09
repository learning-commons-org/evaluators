import { describe, it, expect } from 'vitest';
import { getAvailableGroups, BatchEvaluator, Provider } from '../../../src/batch/index.js';
import type { BatchInput, BatchConfig } from '../../../src/batch/index.js';

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

  it('text-complexity group enforces a row limit of 50', () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    expect(group.maxInputRows).toBe(50);
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

  it('does not throw the limit error when input count equals maxInputRows', async () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const atLimit = makeInputs(group.maxInputRows);
    const boundary = new BatchEvaluator({
      googleApiKey: 'fake-google-key',
      openaiApiKey: 'fake-openai-key',
    });
    const makeStub = () => ({
      evaluate: async () => ({ score: 1, reasoning: 'stub', metadata: {} }),
    });
    const instances = (boundary as unknown as { evaluatorInstances: Map<string, ReturnType<typeof makeStub>> }).evaluatorInstances;
    for (const id of group.evaluatorIds) instances.set(id, makeStub());

    await expect(boundary.evaluate(atLimit, group.id)).resolves.toBeDefined();
  });

  it('error message mentions the bypassRowLimit escape hatch', async () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const tooMany = makeInputs(group.maxInputRows + 1);

    await expect(evaluator.evaluate(tooMany, group.id))
      .rejects.toThrow(/bypassRowLimit/);
  });

  it('explicitly setting bypassRowLimit: false still throws on overflow', async () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const tooMany = makeInputs(group.maxInputRows + 1);
    const strict = new BatchEvaluator({
      googleApiKey: 'fake-google-key',
      openaiApiKey: 'fake-openai-key',
      bypassRowLimit: false,
    });

    await expect(strict.evaluate(tooMany, group.id))
      .rejects.toThrow(`Input exceeds limit for "${group.id}"`);
  });

  it('bypassRowLimit: true skips the row limit check', async () => {
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const tooMany = makeInputs(group.maxInputRows + 1);
    const bypassed = new BatchEvaluator({
      googleApiKey: 'fake-google-key',
      openaiApiKey: 'fake-openai-key',
      bypassRowLimit: true,
    });

    // Pre-populate evaluatorInstances with no-op stubs. initializeEvaluators
    // skips IDs already present in the map, so these stubs survive and
    // executeTask runs against them — no real network calls, no race.
    const makeStub = () => ({
      evaluate: async () => ({ score: 1, reasoning: 'stub', metadata: {} }),
    });
    const instances = (bypassed as unknown as { evaluatorInstances: Map<string, ReturnType<typeof makeStub>> }).evaluatorInstances;
    for (const id of group.evaluatorIds) instances.set(id, makeStub());

    const output = await bypassed.evaluate(tooMany, group.id);
    const expectedTasks = tooMany.length * group.evaluatorIds.length;
    expect(output.summary.totalTasks).toBe(expectedTasks);
    expect(output.summary.successful).toBe(expectedTasks);
    expect(output.summary.failed).toBe(0);
  });

  it('cancel() before evaluation starts returns an empty array', () => {
    const fresh = new BatchEvaluator({ googleApiKey: 'k', openaiApiKey: 'k' });
    expect(fresh.cancel()).toEqual([]);
  });
});

describe('BatchEvaluator — modelOverride config', () => {
  it('stores modelOverride and anthropicApiKey in config', () => {
    const override = { provider: Provider.Anthropic, model: 'claude-opus-4-8' };
    const evaluator = new BatchEvaluator({ anthropicApiKey: 'akey', modelOverride: override });
    const config = (evaluator as unknown as { config: BatchConfig }).config;
    expect(config.modelOverride).toEqual(override);
    expect(config.anthropicApiKey).toBe('akey');
  });

  it('evaluate() runs to completion with modelOverride set', async () => {
    const override = { provider: Provider.Anthropic, model: 'claude-opus-4-8' };
    const group = getAvailableGroups().find((g) => g.id === 'text-complexity')!;
    const evaluator = new BatchEvaluator({ anthropicApiKey: 'akey', modelOverride: override });

    const instances = (evaluator as unknown as { evaluatorInstances: Map<string, unknown> }).evaluatorInstances;
    for (const id of group.evaluatorIds) {
      instances.set(id, { evaluate: async () => ({ score: 'slightly complex', reasoning: 'stub', metadata: {} }) });
    }

    const output = await evaluator.evaluate(makeInputs(1), group.id);
    expect(output.summary.successful).toBe(group.evaluatorIds.length);
    expect(output.summary.failed).toBe(0);
  });
});
