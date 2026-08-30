import { describe, it, expect, vi } from 'vitest';
import { getFamily, BatchEvaluator } from '../../../src/batch/index.js';
import type { BatchInput } from '../../../src/batch/index.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Unit tests for `BatchConfig.llmProvider` (bring-your-own-provider at the batch
 * level). Asserts that the injected provider is plumbed to every evaluator in a
 * group and that a batch can run with no API keys — the batch equivalent of the
 * single-evaluator coverage in tests/unit/evaluators/llm-provider.test.ts.
 */

const FAMILY = getFamily('text-complexity');

function makeFakeProvider(label = 'vertex:gemini-2.5-pro') {
  const generateStructured = vi.fn().mockResolvedValue({
    data: {
      grade: '6-8',
      alternative_grade: '4-5',
      scaffolding_needed: 'Pre-teach vocabulary',
      reasoning: 'Middle-school-appropriate prose.',
    },
    model: label,
    usage: { inputTokens: 100, outputTokens: 50 },
    latencyMs: 10,
  });
  const provider: LLMProvider = {
    label,
    generateStructured,
    generateText: vi
      .fn()
      .mockResolvedValue({ text: '', usage: { inputTokens: 0, outputTokens: 0 }, latencyMs: 0 }),
  };
  return { provider, generateStructured };
}

function makeInputs(count: number): BatchInput[] {
  const text =
    'The mitochondria is the powerhouse of the cell. It produces energy through a process ' +
    'called cellular respiration in eukaryotic organisms.';
  return Array.from({ length: count }, (_, i) => ({
    rowIndex: i + 2,
    columns: { text, grade_level: '6-8' },
    originalRow: { text: 'sample', grade_level: '6-8' },
  }));
}

describe('BatchConfig.llmProvider — bring-your-own-provider', () => {
  it('constructs and runs with no API keys when llmProvider is set', async () => {
    const { provider, generateStructured } = makeFakeProvider();
    const batch = new BatchEvaluator({ llmProvider: provider, telemetry: false });

    const { summary } = await batch.evaluate(makeInputs(1), FAMILY.id);

    // One task per evaluator in the group, all attempted (no missing-key crash).
    expect(summary.totalTasks).toBe(FAMILY.members.length);
    expect(generateStructured).toHaveBeenCalled();
  });

  it('runs every member of the group through the injected provider', async () => {
    const { provider, generateStructured } = makeFakeProvider();
    const batch = new BatchEvaluator({ llmProvider: provider, telemetry: false });

    // One task per member, all attempted, and the injected provider was used
    // (no keys were supplied, so nothing could fall back to a real provider).
    const { results } = await batch.evaluate(makeInputs(1), FAMILY.id);

    expect(results).toHaveLength(FAMILY.members.length);
    expect(generateStructured).toHaveBeenCalled();
    expect(results.some((r) => r.status === 'success')).toBe(true);
  });

  it('never reports a missing-API-key error when llmProvider is set', async () => {
    const { provider } = makeFakeProvider();
    const batch = new BatchEvaluator({ llmProvider: provider, telemetry: false });

    const { results } = await batch.evaluate(makeInputs(1), FAMILY.id);

    for (const r of results) {
      expect(r.error ?? '').not.toMatch(/API key/i);
    }
  });
});
