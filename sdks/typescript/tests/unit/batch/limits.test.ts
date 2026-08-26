import { describe, it, expect, vi } from 'vitest';
import { getAvailableGroups, BatchEvaluator, Provider } from '../../../src/batch/index.js';
import type { BatchInput, BatchConfig, BatchResult } from '../../../src/batch/index.js';
import type { LLMProvider } from '../../../src/providers/base.js';
import type { EvaluatorFamily, FamilyRow, TaskOutcome } from '../../../src/batch/families/family.js';

/**
 * A deterministic stub family for exercising BatchEvaluator orchestration
 * (cancellation, state reset, config plumbing) without real evaluators or
 * network. `evaluate` accepts a family object directly, so no internal poking.
 */
function stubFamily(runTask: (row: FamilyRow, memberId: string) => Promise<TaskOutcome>): EvaluatorFamily {
  const members = [
    { id: 'stub-a', name: 'Stub A' },
    { id: 'stub-b', name: 'Stub B' },
    { id: 'stub-c', name: 'Stub C' },
  ];
  return {
    id: 'stub-family',
    name: 'Stub',
    description: 'stub',
    members,
    columns: [
      { name: 'text', required: true },
      { name: 'grade_level', required: true },
    ],
    maxInputRows: 1000,
    requiredKeys: () => [],
    createRunner: () => ({ members, runTask }),
  };
}

function makeInputs(count: number): BatchInput[] {
  return Array.from({ length: count }, (_, i) => ({
    rowIndex: i + 2,
    columns: { text: 'The cat sat on the mat.', grade_level: '3' },
    originalRow: { text: 'The cat sat on the mat.', grade_level: '3' },
  }));
}

/** A fake provider so QTC evaluators run without network or API keys. */
function fakeProvider(): LLMProvider {
  return {
    label: 'fake:model',
    generateStructured: vi.fn().mockResolvedValue({
      data: { grade: '2-3', alternative_grade: '4-5', scaffolding_needed: '', reasoning: 'stub' },
      model: 'fake:model',
      usage: { inputTokens: 1, outputTokens: 1 },
      latencyMs: 1,
    }),
    generateText: vi.fn().mockResolvedValue({ text: '', usage: { inputTokens: 0, outputTokens: 0 }, latencyMs: 0 }),
  };
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

  it('throws for an unknown familyId', async () => {
    await expect(evaluator.evaluate(makeInputs(1), 'nonexistent-group'))
      .rejects.toThrow('Unknown evaluator family: "nonexistent-group"');
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
    const boundary = new BatchEvaluator({ llmProvider: fakeProvider(), telemetry: false });

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
      llmProvider: fakeProvider(),
      telemetry: false,
      bypassRowLimit: true,
    });

    const output = await bypassed.evaluate(tooMany, group.id);
    const expectedTasks = tooMany.length * group.evaluatorIds.length;
    // The bypass is proven by all rows being processed (totalTasks reflects the
    // over-limit input) rather than the run throwing the limit error.
    expect(output.summary.totalTasks).toBe(expectedTasks);
    expect(output.summary.successful + output.summary.failed).toBe(expectedTasks);
  });

  it('cancel() before evaluation starts returns an empty array', () => {
    const fresh = new BatchEvaluator({ googleApiKey: 'k', openaiApiKey: 'k' });
    expect(fresh.cancel()).toEqual([]);
  });

  it('cancel() mid-evaluation marks queued tasks as cancelled and includes them in completedResults', async () => {
    // concurrency:1 ensures tasks run sequentially so cancel() reliably affects later ones
    const evaluator = new BatchEvaluator({ telemetry: false, concurrency: 1 });

    let firstDone = false;
    const family = stubFamily(async () => {
      if (!firstDone) { firstDone = true; evaluator.cancel(); }
      return { score: 'slightly complex', reasoning: 'stub' };
    });

    const output = await evaluator.evaluate(makeInputs(1), family);
    const successful = output.results.filter(r => r.status === 'success');
    const cancelled = output.results.filter(r => r.status === 'error' && r.error === 'Cancelled by user');

    expect(successful.length).toBeGreaterThanOrEqual(1);
    expect(cancelled.length).toBeGreaterThan(0);
    expect(successful.length + cancelled.length).toBe(family.members.length);

    // Cancelled tasks must be in completedResults so Ctrl+C partial saves are complete
    const completedResults = (evaluator as unknown as { completedResults: BatchResult[] }).completedResults;
    expect(completedResults.length).toBe(family.members.length);
  });

  it('evaluate() resets state between calls — second call produces a clean result set', async () => {
    const evaluator = new BatchEvaluator({ telemetry: false });
    const family = stubFamily(async () => ({ score: 'slightly complex', reasoning: 'stub' }));

    const first = await evaluator.evaluate(makeInputs(1), family);
    const second = await evaluator.evaluate(makeInputs(1), family);

    // Second call must not accumulate results from the first
    expect(second.summary.totalTasks).toBe(family.members.length);
    expect(second.summary.successful).toBe(family.members.length);
    // And first call must be unaffected
    expect(first.summary.totalTasks).toBe(family.members.length);
  });

  it('accepts a bare onProgress callback as the third arg (back-compat)', async () => {
    const evaluator = new BatchEvaluator({ telemetry: false });
    const family = stubFamily(async () => ({ score: 'ok', reasoning: 'stub' }));
    const seen: BatchResult[] = [];
    await evaluator.evaluate(makeInputs(1), family, (r) => seen.push(r));
    expect(seen.length).toBe(family.members.length); // progress still reported
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
    const evaluator = new BatchEvaluator({ anthropicApiKey: 'akey', modelOverride: override, telemetry: false });
    const family = stubFamily(async () => ({ score: 'slightly complex', reasoning: 'stub' }));

    const output = await evaluator.evaluate(makeInputs(1), family);
    expect(output.summary.successful).toBe(family.members.length);
    expect(output.summary.failed).toBe(0);
  });
});

describe('BatchEvaluator.evaluate() — row-level failures and empty input', () => {
  it('returns an empty output for no inputs without constructing a runner', async () => {
    const evaluator = new BatchEvaluator({ telemetry: false });
    const createRunner = vi.fn();
    const family = { ...stubFamily(async () => ({ score: 's', reasoning: '' })), createRunner };

    const output = await evaluator.evaluate([], family);

    expect(output.results).toEqual([]);
    expect(output.summary.totalTasks).toBe(0);
    expect(createRunner).not.toHaveBeenCalled();
  });

  // One key at a time: the hint must fire on either alone, not only on both.
  it.each(['text', 'grade'])(
    'rejects a row in the pre-family shape carrying only %s, naming the fix',
    async (key) => {
      const evaluator = new BatchEvaluator({ telemetry: false });
      const family = stubFamily(async () => ({ score: 's', reasoning: '' }));
      // Without the shape check this reached Object.keys(undefined) and threw a bare
      // "Cannot convert undefined or null to object", naming nothing.
      const legacy = [{ [key]: '3', rowIndex: 2, originalRow: {} }];

      await expect(evaluator.evaluate(legacy as never, family)).rejects.toThrow(
        /row 2: expected a "columns" record.*received undefined.*predate family-aware input/s,
      );
    },
  );

  it.each([
    ['null', null, 'null'],
    ['an array', ['text', 'grade'], 'an array'],
    ['a string', 'text,grade', 'string'],
  ])('rejects columns given as %s, reporting what it received', async (_label, columns, received) => {
    const evaluator = new BatchEvaluator({ telemetry: false });
    const family = stubFamily(async () => ({ score: 's', reasoning: '' }));
    const bad = [{ rowIndex: 7, columns, originalRow: {} }];

    const run = evaluator.evaluate(bad as never, family);
    await expect(run).rejects.toThrow(`received ${received}.`);
    // No legacy keys, so the generic guidance applies rather than the migration hint.
    await expect(run).rejects.toThrow(/supply columns explicitly/);
  });

  it('turns a row that fails normalization into per-member errors without losing the good rows', async () => {
    const evaluator = new BatchEvaluator({ telemetry: false });
    const family = stubFamily(async () => ({ score: 'slightly complex', reasoning: 'ok' }));
    const seen: BatchResult[] = [];

    // Header validation passes on row 1, so the empty `grade_level` is caught per row.
    // parseCSV trims, so an empty cell arrives as '' — what normalizeRow rejects.
    const inputs: BatchInput[] = [
      { rowIndex: 2, columns: { text: 'fine', grade_level: '3' }, originalRow: { text: 'fine', grade_level: '3' } },
      { rowIndex: 3, columns: { text: 'bad', grade_level: '' }, originalRow: { text: 'bad', grade_level: '' } },
    ];

    const output = await evaluator.evaluate(inputs, family, { onProgress: (r) => seen.push(r) });

    const failed = output.results.filter((r) => r.status === 'error');
    const ok = output.results.filter((r) => r.status === 'success');
    expect(failed).toHaveLength(family.members.length);
    expect(ok).toHaveLength(family.members.length);
    expect(failed.every((r) => r.rowIndex === 3)).toBe(true);
    expect(new Set(failed.map((r) => r.evaluatorId)).size).toBe(family.members.length);
    // Reported through the same progress channel as evaluated rows.
    expect(seen.filter((r) => r.status === 'error')).toHaveLength(family.members.length);
  });
});
