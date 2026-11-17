import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
} from '../../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/vocabulary-complexity.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';

/**
 * The two evaluators neither factory drives read a step's reasoning effort themselves, so
 * each is tested here against its own contract with an effort declared on every step. No
 * registered contract declares one for them yet; these are the values their providers admit.
 */

// Hoisted with the mocks below, which run before the module body.
const { withEfforts, calls } = vi.hoisted(() => {
  const EFFORTS: Record<string, string> = {
    // Math Standards Alignment: both steps are on anthropic.
    evaluate_math_standards_alignment: 'high',
    coarse_filter: 'low',
    // Vocabulary Complexity: background and grades 5-12 on openai, grades 3-4 on google.
    background_knowledge: 'none',
    vocab_complexity_grades_3_4: 'minimal',
    vocab_complexity_other_grades: 'medium',
  };
  return {
    withEfforts(config: unknown) {
      const copy = structuredClone((config as { default: { steps: Array<{ id: string; generation: object }> } }).default);
      for (const step of copy.steps) {
        if (EFFORTS[step.id]) Object.assign(step.generation, { reasoning_effort: EFFORTS[step.id] });
      }
      return { default: copy };
    },
    /** Every call a built-in provider was asked to make, with `reasoningEffort` only if passed. */
    calls: [] as Array<{ model: string; kind: 'structured' | 'text'; reasoningEffort?: string; coarse?: boolean }>,
  };
});

vi.mock(
  '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/config.json',
  async (importOriginal) => withEfforts(await importOriginal()),
);
vi.mock(
  '../../../../../evals/text-complexity/ela-reading/vocabulary-complexity/config.json',
  async (importOriginal) => withEfforts(await importOriginal()),
);

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => ({
      label: `${config.type}:${config.model}`,
      generateStructured: vi.fn((req: { messages: Array<{ role: string }>; reasoningEffort?: string }) => {
        const coarse = req.messages.every((m) => m.role !== 'system');
        calls.push({
          model: config.model,
          kind: 'structured',
          coarse,
          ...('reasoningEffort' in req ? { reasoningEffort: req.reasoningEffort } : {}),
        });
        return Promise.resolve({
          data: config.type === 'anthropic'
            ? coarse
              ? { standards: [{ standard: '3.MD.C.7.d', relevant: true }] }
              : { evaluations: [{ lc_id: 'lc-1', reasoning: 'r', answer: 'Yes', feedback: null }] }
            : { complexity_score: 'moderately_complex', reasoning: 'r', factors: [] },
          model: config.model,
          usage: { inputTokens: 1, outputTokens: 1 },
          latencyMs: 1,
        });
      }),
      generateText: vi.fn((_messages: unknown, _temperature: unknown, ...rest: unknown[]) => {
        calls.push({
          model: config.model,
          kind: 'text',
          ...(rest.length > 0 && rest[0] !== undefined ? { reasoningEffort: rest[0] as string } : {}),
        });
        return Promise.resolve({ text: 'assumed', usage: { inputTokens: 1, outputTokens: 1 }, latencyMs: 1 });
      }),
    })),
  };
});

beforeEach(() => {
  calls.length = 0;
});

const OVERRIDE = { modelOverride: { provider: Provider.OpenAI, model: 'gpt-5.5' }, openaiApiKey: 'k' };

describe('Math Standards Alignment reasoning effort', () => {
  const kg = () =>
    ({
      getLearningComponentsByCode: vi.fn().mockResolvedValue({
        uuid: 'u',
        statementCode: '3.MD.C.7.d',
        normalizedCode: '3.MD.C.7.D',
        description: 'd',
        components: [{ identifier: 'lc-1', description: 'c' }],
      }),
      getStandardInfo: vi.fn().mockResolvedValue({
        uuid: 'u',
        statementCode: '3.MD.C.7.d',
        normalizedCode: '3.MD.C.7.D',
        description: 'd',
      }),
    }) as unknown as KnowledgeGraphClient;

  const run = (overrides: Record<string, unknown> = {}) =>
    new MathStandardsAlignmentEvaluator({
      anthropicApiKey: 'k',
      learningCommonsApiKey: 'k',
      telemetry: false,
      _kgClient: kg(),
      ...overrides,
    }).evaluateItems([{ question: 'What is 12 + 7?', statement_codes: ['3.MD.C.7.d'] }], Jurisdiction.MultiState, {
      useCoarseFilter: true,
    });

  it('sends each step its own declared effort', async () => {
    await run();

    expect(calls.filter((c) => c.coarse).map((c) => c.reasoningEffort)).toEqual(['low']);
    expect(calls.filter((c) => !c.coarse).map((c) => c.reasoningEffort)).toEqual(['high']);
  });

  it('drops only the coarse effort when coarseFilterModel replaces that model', async () => {
    await run({ coarseFilterModel: 'claude-something-else' });

    expect(calls.find((c) => c.coarse)).not.toHaveProperty('reasoningEffort');
    expect(calls.find((c) => !c.coarse)?.reasoningEffort).toBe('high');
  });

  it('drops every effort under modelOverride', async () => {
    await run(OVERRIDE);

    expect(calls.length).toBeGreaterThan(0);
    expect(calls.every((c) => !('reasoningEffort' in c))).toBe(true);
  });
});

describe('Vocabulary Complexity reasoning effort', () => {
  const evaluate = (grade: '3' | '7', overrides: Record<string, unknown> = {}) =>
    new VocabularyComplexityEvaluator({
      googleApiKey: 'k',
      openaiApiKey: 'k',
      telemetry: false,
      ...overrides,
    }).evaluate({ text: 'The mitochondria is the powerhouse of the cell.', grade_level: grade });

  it.each([
    ['3', 'minimal'],
    ['7', 'medium'],
  ] as const)('grade %s sends the background step its effort and its band step %s', async (grade, band) => {
    await evaluate(grade);

    expect(calls.map((c) => [c.kind, c.reasoningEffort])).toEqual([
      ['text', 'none'],
      ['structured', band],
    ]);
  });

  it('drops every effort under modelOverride', async () => {
    await evaluate('3', OVERRIDE);

    expect(calls).toHaveLength(2);
    expect(calls.every((c) => !('reasoningEffort' in c))).toBe(true);
  });
});
