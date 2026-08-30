import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
} from '../../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
import type { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import CONFIG from '../../../../../evals/academic-standards-alignment/mathematics/math-standards-alignment/config.json';

/**
 * Math Standards Alignment is the one evaluator neither factory drives, so nothing
 * generic checks that it uses the values its contract declares. These tests do, per step.
 *
 * It declares two steps with two models: `coarse_filter` and
 * `evaluate_math_standards_alignment`. They are pinned to the same model today, which is
 * exactly why this needs asserting — a re-pin of one would otherwise silently move the
 * other, or fail to move it.
 */

const created: Array<{ type: string; model: string }> = [];
const calls: Array<{ model: string; temperature?: number; user: string }> = [];

/**
 * What the coarse filter says about the standard under test. `true` sends it on to be
 * evaluated; `false` is what produces a coarse-filtered result, which is the only path
 * where a missing learning-component prefetch shows up as a count.
 */
let coarseRelevant = true;

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      created.push(config);
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn(
          (req: {
            messages: Array<{ role: string; content: string }>;
            temperature?: number;
          }) => {
            calls.push({
              model: config.model,
              temperature: req.temperature,
              user: req.messages.find((m) => m.role === 'user')?.content ?? '',
            });

            // The coarse filter and the detail step take different shapes; the coarse
            // prompt is the one that lists candidate standards.
            const isCoarse = req.messages.every((m) => m.role !== 'system');
            return Promise.resolve({
              data: isCoarse
                ? { standards: [{ standard: '3.MD.C.7.d', relevant: coarseRelevant }] }
                : {
                    evaluations: [
                      {
                        lc_id: 'lc-1',
                        reasoning: 'The question asks students to do exactly this.',
                        answer: 'Yes',
                        feedback: null,
                      },
                    ],
                  },
              model: config.model,
              usage: { inputTokens: 5, outputTokens: 2 },
              latencyMs: 3,
            });
          },
        ),
        generateText: vi.fn(),
      };
    }),
  };
});

const STEPS = Object.fromEntries(CONFIG.steps.map((s) => [s.id, s]));
const DETAIL_STEP = STEPS['evaluate_math_standards_alignment'];
const COARSE_STEP = STEPS['coarse_filter'];

/** Enough of the Knowledge Graph for one question against one standard. */
function stubKgClient(): KnowledgeGraphClient {
  return {
    getLearningComponentsByCode: vi.fn().mockResolvedValue({
      uuid: 'standard-uuid',
      statementCode: '3.MD.C.7.d',
      normalizedCode: '3.MD.C.7.D',
      description: 'Recognize area as additive.',
      components: [{ identifier: 'lc-1', description: 'Decompose rectilinear figures' }],
    }),
    getStandardInfo: vi.fn().mockResolvedValue({
      uuid: 'standard-uuid',
      statementCode: '3.MD.C.7.d',
      normalizedCode: '3.MD.C.7.D',
      description: 'Recognize area as additive.',
    }),
  } as unknown as KnowledgeGraphClient;
}

function construct(overrides: Record<string, unknown> = {}) {
  return new MathStandardsAlignmentEvaluator({
    anthropicApiKey: 'k',
    learningCommonsApiKey: 'k',
    telemetry: false,
    _kgClient: stubKgClient(),
    ...overrides,
  });
}

beforeEach(() => {
  created.length = 0;
  calls.length = 0;
  coarseRelevant = true;
});

describe('MathStandardsAlignmentEvaluator — contract bindings', () => {
  it('declares two steps with a model and temperature each', () => {
    // If the contract stops declaring these, the assertions below would pass vacuously.
    expect(DETAIL_STEP, 'contract must declare the detail step').toBeDefined();
    expect(COARSE_STEP, 'contract must declare the coarse filter step').toBeDefined();
    for (const step of [DETAIL_STEP, COARSE_STEP]) {
      expect(step.model.name).toBeTruthy();
      expect(step.generation.temperature).toBeTypeOf('number');
    }
  });

  it('builds each provider with the model its own step declares', () => {
    construct();

    expect(created.map((c) => c.model)).toEqual([DETAIL_STEP.model.name, COARSE_STEP.model.name]);
    expect(created.every((c) => c.type === 'anthropic')).toBe(true);
  });

  it('lets coarseFilterModel override only the coarse step', () => {
    construct({ coarseFilterModel: 'claude-something-else' });

    expect(created.map((c) => c.model)).toEqual([DETAIL_STEP.model.name, 'claude-something-else']);
  });

  it('sends the detail step its declared temperature', async () => {
    await construct().evaluate({
      question: 'A playground is shaped like an L. What is its area?',
      statementCode: '3.MD.C.7.d',
      jurisdiction: Jurisdiction.MultiState,
    });

    expect(calls).toHaveLength(1);
    expect(calls[0].model).toBe(DETAIL_STEP.model.name);
    expect(calls[0].temperature).toBe(DETAIL_STEP.generation.temperature);
  });

  it('sends the coarse filter step its own declared temperature', async () => {
    // The coarse filter only runs for a bulk call that opts into it.
    await construct().evaluateItems(
      [{ question: 'What is 12 + 7?', statementCodes: ['3.MD.C.7.d'] }],
      Jurisdiction.MultiState,
      { useCoarseFilter: true },
    );

    const coarse = calls.filter((c) => !c.user.includes('learning'));
    expect(coarse.length, 'the coarse filter should have run').toBeGreaterThan(0);
    for (const call of coarse) {
      expect(call.model).toBe(COARSE_STEP.model.name);
      expect(call.temperature).toBe(COARSE_STEP.generation.temperature);
    }
  });

  it('substitutes every placeholder its steps declare', async () => {
    await construct().evaluate({
      question: 'A playground is shaped like an L. What is its area?',
      statementCode: '3.MD.C.7.d',
      jurisdiction: Jurisdiction.MultiState,
    });

    // A placeholder the prompt module does not know about is left as `{name}` and reaches
    // the model verbatim, which reads as an instruction rather than as an error.
    for (const name of Object.keys(DETAIL_STEP.prompt.placeholders)) {
      expect(calls[0].user, `{${name}} should be substituted`).not.toContain(`{${name}}`);
    }
  });

  it('reports the standard it was asked about', async () => {
    const { result } = await construct().evaluate({
      question: 'A playground is shaped like an L. What is its area?',
      statementCode: '3.MD.C.7.d',
      jurisdiction: Jurisdiction.MultiState,
    });

    expect(result.statementCode).toBe('3.MD.C.7.d');
    expect(result.totalCount).toBe(1);
    expect(result.alignedCount).toBe(1);
    expect(result.learningComponents[0].description).toBe('Decompose rectilinear figures');
  });
});

describe('a failed learning-component prefetch is reported, not silently zero', () => {
  it('carries the error on a coarse-filtered result', async () => {
    // `totalCount` falls back to 0 when the prefetch fails, which reads exactly like a
    // standard that has no learning components. The error is what tells the two apart —
    // the field already means "0 because nothing was measured, not because nothing
    // aligned".
    const failing = {
      getLearningComponentsByCode: vi.fn().mockRejectedValue(new Error('KG unavailable')),
      getStandardInfo: vi.fn().mockResolvedValue({
        uuid: 'standard-uuid',
        statementCode: '3.MD.C.7.d',
        normalizedCode: '3.MD.C.7.D',
        description: 'Recognize area as additive.',
      }),
    } as unknown as KnowledgeGraphClient;

    const evaluator = new MathStandardsAlignmentEvaluator({
      anthropicApiKey: 'k',
      learningCommonsApiKey: 'k',
      telemetry: false,
      _kgClient: failing,
    });

    // Filtered out, so the standard is never evaluated: the only remaining source of an
    // error on this result is the prefetch. With the standard marked relevant the
    // evaluation path fails too, and this test passed with the fix reverted.
    coarseRelevant = false;

    const [item] = await evaluator.evaluateItems(
      [{ question: 'What is 12 + 7?', statementCodes: ['3.MD.C.7.d'] }],
      Jurisdiction.MultiState,
      { useCoarseFilter: true },
    );

    const [standard] = item.standards;
    expect(standard.coarseFiltered, 'must reach the coarse-filtered branch').toBe(true);
    expect(standard.totalCount).toBe(0);
    expect(standard.error?.message, 'the failure must reach the caller').toContain(
      'KG unavailable',
    );
  });
});
