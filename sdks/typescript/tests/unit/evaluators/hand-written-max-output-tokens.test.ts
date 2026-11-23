import { describe, it, expect, vi, beforeEach } from 'vitest';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/vocabulary-complexity.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * Vocabulary Complexity reads its generation settings itself, so it must also read each
 * step's `generation.max_output_tokens`, including the background-knowledge step that runs
 * through `generateText`. The contract here declares a distinct cap on each of its steps.
 */

// Hoisted with the mocks below, which run before the module body.
const { CAPS, withCaps } = vi.hoisted(() => {
  const CAPS: Record<string, number> = {
    background_knowledge: 1500,
    vocab_complexity_grades_3_4: 3000,
    vocab_complexity_other_grades: 4000,
  };
  return {
    CAPS,
    withCaps(config: unknown) {
      const copy = structuredClone((config as { default: { steps: Array<{ id: string; generation: object }> } }).default);
      for (const step of copy.steps) {
        step.generation = { ...step.generation, max_output_tokens: CAPS[step.id] };
      }
      return { default: copy };
    },
  };
});

vi.mock(
  '../../../../../evals/text-complexity/ela-reading/vocabulary-complexity/config.json',
  async (importOriginal) => withCaps(await importOriginal()),
);
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(
    (config: { type: string; model: string }): LLMProvider => ({
      label: `${config.type}:${config.model}`,
      generateStructured: vi.fn().mockResolvedValue({
        data: { complexity_score: 'moderately_complex', reasoning: 'r', factors: [] },
        model: config.model,
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      }),
      generateText: vi.fn().mockResolvedValue({
        text: 'An assumption.',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      }),
    }),
  ),
}));
vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

const KEYS = { googleApiKey: 'k', openaiApiKey: 'k', telemetry: false } as const;

/** The evaluator's three providers, read off it as the vocabulary tests do. */
function providersOf(evaluator: VocabularyComplexityEvaluator) {
  const e = evaluator as unknown as Record<string, LLMProvider>;
  return {
    background: e.backgroundKnowledgeProvider,
    grades34: e.grades34ComplexityProvider,
    other: e.otherGradesComplexityProvider,
  };
}

describe('Vocabulary Complexity output caps', () => {
  beforeEach(() => vi.clearAllMocks());

  it('sends each step its own cap, the prose step as generateText options', async () => {
    const evaluator = new VocabularyComplexityEvaluator(KEYS);
    const { background, grades34, other } = providersOf(evaluator);

    await evaluator.evaluate({ text: 'The cat sat on the mat.', grade_level: '3' });
    expect(vi.mocked(background.generateText).mock.calls[0][2]).toEqual({
      maxTokens: CAPS.background_knowledge,
    });
    expect(vi.mocked(grades34.generateStructured).mock.calls[0][0].maxTokens).toBe(
      CAPS.vocab_complexity_grades_3_4,
    );

    await evaluator.evaluate({ text: 'The cat sat on the mat.', grade_level: '7' });
    expect(vi.mocked(other.generateStructured).mock.calls[0][0].maxTokens).toBe(
      CAPS.vocab_complexity_other_grades,
    );
  });

  it('drops every cap under modelOverride', async () => {
    const evaluator = new VocabularyComplexityEvaluator({
      ...KEYS,
      anthropicApiKey: 'k',
      modelOverride: { provider: Provider.Anthropic, model: 'claude-opus-5-5' },
    });
    const { background, other } = providersOf(evaluator);

    await evaluator.evaluate({ text: 'The cat sat on the mat.', grade_level: '7' });
    // No options argument at all, so a two-argument provider is called as before.
    expect(vi.mocked(background.generateText).mock.calls[0]).toHaveLength(2);
    expect(vi.mocked(other.generateStructured).mock.calls[0][0]).not.toHaveProperty('maxTokens');
  });

  it('does not hand an injected llmProvider any cap', async () => {
    const llmProvider: LLMProvider = {
      label: 'mine',
      generateStructured: vi.fn().mockResolvedValue({
        data: { complexity_score: 'moderately_complex', reasoning: 'r', factors: [] },
        model: 'mine',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      }),
      generateText: vi.fn().mockResolvedValue({
        text: 'An assumption.',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      }),
    };
    await new VocabularyComplexityEvaluator({ telemetry: false, llmProvider }).evaluate({
      text: 'The cat sat on the mat.',
      grade_level: '3',
    });

    expect(vi.mocked(llmProvider.generateText).mock.calls[0]).toHaveLength(2);
    expect(vi.mocked(llmProvider.generateStructured).mock.calls[0][0]).not.toHaveProperty('maxTokens');
  });
});
