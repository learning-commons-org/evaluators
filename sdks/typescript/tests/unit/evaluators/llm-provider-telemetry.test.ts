import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/grade-level-appropriateness.js';
import { SentenceStructureEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/sentence-structure.js';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/vocabulary-complexity.js';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
} from '../../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
import type { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Telemetry marks an injected `llmProvider` as `custom:{label}` (spec §3.4).
 *
 * Its label is the caller's own word, so a client labelled `openai:gpt-4o` must
 * never be counted as our OpenAI adapter. The result's `metadata.model` keeps the
 * label as given. One case per code path that names a provider in telemetry:
 * single-step, the multi-step factory, Vocabulary Complexity, and Math Standards
 * Alignment.
 */

const sent = vi.fn();

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = sent;
  },
}));

const built: Array<{ type: string; model: string }> = [];

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      built.push(config);
      return provider(`${config.type}:${config.model}`, () => GLA_DATA);
    }),
  };
});

const TEXT =
  'The mitochondria is the powerhouse of the cell. It produces energy through a process ' +
  'called cellular respiration in eukaryotic organisms.';

const GLA_DATA = {
  grade_band: '6-8',
  alternative_grade_band: '4-5',
  scaffolding_needed: 'Pre-teach vocabulary; use diagrams',
  reasoning: 'Middle-school-appropriate science prose.',
};

const SENTENCE_ANALYSIS = {
  reasoning: 'Mock analysis',
  num_sentences: 2,
  num_words: 10,
  flesch_kincaid_grade: 3.5,
  num_simple_sentences: 2,
  num_compound_sentences: 0,
  num_complex_sentences: 0,
  num_compound_complex_sentences: 0,
  num_other_sentences: 0,
  num_independent_clauses: 2,
  num_subordinate_clauses: 0,
  num_total_clauses: 2,
  num_sentences_with_subordinate: 0,
  num_sentences_with_multiple_subordinates: 0,
  num_sentences_with_embedded_clauses: 0,
  num_prepositional_phrases: 1,
  num_participle_phrases: 0,
  num_appositive_phrases: 0,
  num_simple_transitions: 0,
  num_sophisticated_transitions: 0,
  words_in_simple_sentences: 10,
  words_in_compound_sentences: 0,
  words_in_complex_sentences: 0,
  words_in_compound_complex_sentences: 0,
  words_in_other_sentences: 0,
  sentence_word_counts: [5, 5],
  num_one_concept_sentences: 2,
  num_multi_concept_sentences: 0,
  num_cleft_sentences: 0,
  max_clauses_in_any_sentence: 1,
  num_compound: 0,
  num_basic_complex: 0,
  num_advanced_complex: 0,
  percentage_simple: 100,
  percentage_compound: 0,
  percentage_basic_complex: 0,
  percentage_advanced_complex: 0,
};

const COMPLEXITY = { complexity_score: 'slightly_complex', reasoning: 'Simple sentences.' };

const MATH_DETAIL = {
  evaluations: [
    { lc_id: 'lc-1', reasoning: 'Asks for exactly this.', answer: 'Yes', feedback: null },
  ],
};

/** A provider answering every structured call with `answer(n)`, `n` counting from 0. */
function provider(label: string, answer: (n: number) => unknown): LLMProvider {
  let n = 0;
  return {
    label,
    generateStructured: vi.fn(async () => ({
      data: answer(n++),
      model: label,
      usage: { inputTokens: 5, outputTokens: 2 },
      latencyMs: 1,
    })) as LLMProvider['generateStructured'],
    generateText: vi.fn(async () => ({
      text: 'Students know basic cell biology.',
      usage: { inputTokens: 5, outputTokens: 2 },
      latencyMs: 1,
    })),
  };
}

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

interface Event {
  status: string;
  provider: string;
  metadata?: { stage_details?: Array<{ stage: string; provider: string }> };
}

/** The one event the evaluation sent, once the fire-and-forget send has run. */
async function event(): Promise<Event> {
  await vi.waitFor(() => expect(sent).toHaveBeenCalledTimes(1));
  return sent.mock.calls[0][0] as Event;
}

type Run = (llmProvider?: LLMProvider) => Promise<{ metadata: { model: string } }>;

const PATHS: Array<{ path: string; answer: (n: number) => unknown; run: Run }> = [
  {
    path: 'single-step',
    answer: () => GLA_DATA,
    run: (llmProvider) =>
      new GradeLevelAppropriatenessEvaluator({ googleApiKey: 'k', llmProvider }).evaluate({
        text: TEXT,
      }),
  },
  {
    path: 'multi-step',
    answer: (n) => (n === 0 ? SENTENCE_ANALYSIS : COMPLEXITY),
    run: (llmProvider) =>
      new SentenceStructureEvaluator({ openaiApiKey: 'k', llmProvider }).evaluate({
        text: TEXT,
        grade_level: '3',
      }),
  },
  {
    path: 'vocabulary complexity',
    answer: () => ({ ...COMPLEXITY, factors: ['Academic terms'] }),
    run: (llmProvider) =>
      new VocabularyComplexityEvaluator({
        openaiApiKey: 'k',
        googleApiKey: 'k',
        llmProvider,
      }).evaluate({ text: TEXT, grade_level: '5' }),
  },
  {
    path: 'math standards alignment',
    answer: () => MATH_DETAIL,
    run: (llmProvider) =>
      new MathStandardsAlignmentEvaluator({
        anthropicApiKey: 'k',
        learningCommonsApiKey: 'k',
        _kgClient: stubKgClient(),
        llmProvider,
      }).evaluate({
        question: 'A playground is shaped like an L. What is its area?',
        statement_code: '3.MD.C.7.d',
        jurisdiction: Jurisdiction.MultiState,
      }),
  },
];

/** Every provider a model string names, split on the `+` that joins several. */
const named = (model: string) => model.split('+');

beforeEach(() => {
  sent.mockReset();
  sent.mockResolvedValue(undefined);
  built.length = 0;
});

describe('telemetry marks an injected llmProvider', () => {
  describe.each(PATHS)('$path', ({ answer, run }) => {
    it.each(['acme-gateway', 'openai:gpt-4o', 'custom:acme'])(
      'reports %s as custom:<label> and returns it unmarked',
      async (label) => {
        const result = await run(provider(label, answer));

        expect(built).toEqual([]);
        expect(named(result.metadata.model).every((m) => m === label)).toBe(true);
        const { provider: reported, metadata } = await event();
        expect(named(reported).every((p) => p === `custom:${label}`)).toBe(true);
        const stages = metadata?.stage_details ?? [];
        expect(stages.length).toBeGreaterThan(0);
        expect(stages.every((s) => s.provider === `custom:${label}`)).toBe(true);
      },
    );

    it('marks it on a failed evaluation too', async () => {
      const failing = provider('openai:gpt-4o', answer);
      vi.mocked(failing.generateStructured).mockRejectedValue(
        Object.assign(new Error('nope'), { statusCode: 401 }),
      );
      vi.mocked(failing.generateText).mockRejectedValue(
        Object.assign(new Error('nope'), { statusCode: 401 }),
      );

      await expect(run(failing)).rejects.toThrow();

      const { status, provider: reported } = await event();
      expect(status).toBe('error');
      expect(named(reported).every((p) => p === 'custom:openai:gpt-4o')).toBe(true);
    });

    it('leaves a built-in adapter unmarked', async () => {
      await run().catch(() => undefined);

      const { provider: reported } = await event();
      expect(built.length).toBeGreaterThan(0);
      expect(named(reported).some((p) => p.startsWith('custom:'))).toBe(false);
    });
  });
});
