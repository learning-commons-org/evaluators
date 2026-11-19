import { describe, it, expect, vi } from 'vitest';
import { MathStandardsAlignmentEvaluator } from '../../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/vocabulary-complexity.js';
import type { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';

/**
 * The evaluators neither factory drives do not send a reasoning effort yet, so a contract
 * declaring one is refused at construction rather than run at the model's default. Each
 * contract here declares one on a single step.
 */

// Hoisted with the mocks below, which run before the module body.
const { withEffortOn } = vi.hoisted(() => ({
  withEffortOn(stepId: string) {
    return (config: unknown) => {
      const copy = structuredClone((config as { default: { steps: Array<{ id: string; generation: object }> } }).default);
      for (const step of copy.steps) {
        if (step.id === stepId) step.generation = { temperature: null, reasoning_effort: 'low' };
      }
      return { default: copy };
    };
  },
}));

vi.mock(
  '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/config.json',
  async (importOriginal) => withEffortOn('coarse_filter')(await importOriginal()),
);
vi.mock(
  '../../../../../evals/text-complexity/ela-reading/vocabulary-complexity/config.json',
  async (importOriginal) => withEffortOn('background_knowledge')(await importOriginal()),
);
vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

describe('hand-written evaluators refuse a declared reasoning effort', () => {
  it('Math Standards Alignment', () => {
    expect(
      () =>
        new MathStandardsAlignmentEvaluator({
          anthropicApiKey: 'k',
          learningCommonsApiKey: 'k',
          telemetry: false,
          _kgClient: {} as KnowledgeGraphClient,
        }),
    ).toThrow(/does not support generation\.reasoning_effort yet; .* coarse_filter/);
  });

  it('Vocabulary Complexity', () => {
    expect(
      () => new VocabularyComplexityEvaluator({ googleApiKey: 'k', openaiApiKey: 'k', telemetry: false }),
    ).toThrow(/does not support generation\.reasoning_effort yet; .* background_knowledge/);
  });
});
