import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { SentenceStructureEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/sentence-structure.js';
import { ConfigurationError } from '../../../src/errors.js';
import { Provider } from '../../../src/evaluators/base.js';
import type { LLMProvider } from '../../../src/providers/base.js';
import { addEngineeredFeatures, featuresToJSON } from '../../../src/features/sentence-features.js';
import CONFIG from '../../../../../evals/text-complexity/ela-reading/sentence-structure/config.json';

// Derived from the contract rather than copied from it, so a model re-pin in
// config.json surfaces here instead of the test quietly asserting a stale value.
const stepsFor = (grade: string) => CONFIG.steps.filter((step) => step.condition.in.includes(grade));

/** The model the envelope reports for a grade: that of the last step the grade runs. */
const expectedModel = (grade: string) => {
  const steps = stepsFor(grade);
  const last = steps[steps.length - 1];
  return `${last.model.provider}:${last.model.name}`;
};

// Helper to create minimal valid sentence analysis mock
const createMockSentenceAnalysis = () => ({
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
});

// Mock providers
const createMockProvider = (config?: { type?: string; model?: string }): LLMProvider => ({
  label: config?.type && config?.model ? `${config.type}:${config.model}` : 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
});

// Mock the createProvider factory
vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn((config) => createMockProvider(config)),
}));

// Mock telemetry to avoid real HTTP calls
vi.mock('../../../src/telemetry/client.js', () => {
  return {
    TelemetryClient: class MockTelemetryClient {
      send = vi.fn().mockResolvedValue(undefined);
    },
  };
});

describe('SentenceStructureEvaluator - Constructor Validation', () => {
  it('should throw ConfigurationError when OpenAI API key is missing', () => {
    expect(() => new SentenceStructureEvaluator({
      openaiApiKey: '',
    })).toThrow(ConfigurationError);
  });

});

describe('SentenceStructureEvaluator - Evaluation Flow', () => {
  let evaluator: SentenceStructureEvaluator;
  let mockProvider: LLMProvider;

  /**
   * Point `mockProvider` at the provider a grade runs on. Each grade band has its own
   * model, and both stages of a band share one provider instance.
   */
  const useProviderFor = (grade: string) => {
    // @ts-expect-error Accessing private property for testing
    const providers: Map<string, LLMProvider> = evaluator.providers;
    mockProvider = providers.get(stepsFor(grade)[0].id)!;
  };

  beforeEach(() => {
    vi.clearAllMocks();

    // Create evaluator (providers will be mocked)
    evaluator = new SentenceStructureEvaluator({
      openaiApiKey: 'test-openai-key',
      telemetry: false,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Successful Evaluation Flow', () => {
    it('should successfully evaluate text through both stages', async () => {
      const testText = 'The cat sat on the mat. It was sleeping peacefully.';
      const testGrade = '3';
      useProviderFor(testGrade);

      // Stage 1: sentence analysis, Stage 2: complexity classification — same provider
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'stub-model',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockResolvedValueOnce({
          data: {
            complexity_score: 'slightly_complex',
            reasoning: 'The text uses simple sentence structures appropriate for third grade.',
          },
          model: 'stub-model',
          usage: { inputTokens: 250, outputTokens: 80 },
          latencyMs: 500,
        });

      // Execute evaluation
      const result = await evaluator.evaluate({ text: testText, grade_level: testGrade });

      // Verify result structure
      expect(result.result.complexity_score).toBe('slightly_complex');
      expect(result.result.reasoning).toContain('simple sentence structures');
      expect(result.metadata).toBeDefined();
      expect(result.metadata.model).toBe(expectedModel(testGrade));
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      // Token usage is aggregated across both stages: stage 1 (150/100) + stage 2 (250/80)
      expect(result.metadata.tokenUsage.inputTokens).toBe(400);
      expect(result.metadata.tokenUsage.outputTokens).toBe(180);

      // Verify provider was called twice (once per stage)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);

      // output_schema.json declares the classify step's output only, so the analysis
      // step's ~30 grammatical counts are not surfaced.
      expect(result.result).not.toHaveProperty('sentenceAnalysis');
      expect(result.result).not.toHaveProperty('features');
    });
  });

  it.each(['3', '4'] as const)('floors raw features and uses explicit rubric boundaries for grade %s', async (grade) => {
    useProviderFor(grade);
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: {
          ...createMockSentenceAnalysis(),
          num_sentences: 25,
          num_words: 299,
          sentence_word_counts: [...Array(24).fill(12), 11],
          flesch_kincaid_grade: -0.4,
          num_subordinate_clauses: 1,
          num_simple_transitions: 1,
          num_appositive_phrases: 1,
          num_participle_phrases: 1,
        },
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 0,
      })
      .mockResolvedValueOnce({
        data: { complexity_score: 'slightly_complex', reasoning: 'Mock classification' },
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 0,
      });

    await evaluator.evaluate({ text: 'Test passage.', grade_level: grade });
    const messages = vi.mocked(mockProvider.generateStructured).mock.calls[1][0].messages;
    const prompt = messages.map((message) => message.content).join('\n');
    const features = JSON.parse(prompt.split('# TEXT STATISTICS\n')[1]);
    expect(features.avg_subordinates_per_sentence).toBe(0);
    expect(features.avg_transitions_per_sentence).toBe(0);
    expect(features.appositive_phrase_density).toBe(0);
    expect(features.participle_phrase_density).toBe(0);
    expect(features.avg_words_per_sentence).toBe(11);
    expect(features.flesch_kincaid_grade).toBe(-1);
    expect(prompt).not.toContain('typically between ');
    expect(prompt).not.toContain(' > ');
    expect(prompt).toContain('>= ');
    expect(prompt).not.toContain('avg_sentence_length');
    expect(prompt.match(/`avg_words_per_sentence`/g)).toHaveLength(4);
  });

  it.each([
    ['3', 'num_sentences_with_subordinate', 624, 2500, 24, 25, false],
    ['3', 'num_sentences_with_subordinate', 449, 1000, 44, 45, false],
    ['3', 'num_sentences_with_subordinate', 1124, 2500, 44, 45, false],
    ['3', 'num_sentences_with_subordinate', 45, 100, 45, 45, true],
    ['3', 'num_simple_sentences', 1499, 2500, 59, 60, false],
    ['3', 'num_simple_sentences', 3, 5, 60, 60, true],
    ['3', 'num_simple_sentences', 121, 200, 60, 60, true],
    ['4', 'num_sentences_with_subordinate', 749, 2500, 29, 30, false],
    ['4', 'num_sentences_with_subordinate', 1249, 2500, 49, 50, false],
    ['4', 'num_sentences_with_subordinate', 1, 2, 50, 50, true],
    ['4', 'num_sentences_with_multiple_subordinates', 199, 2500, 7, 8, false],
    ['4', 'num_sentences_with_multiple_subordinates', 2, 25, 8, 8, true],
  ] as const)('percentage boundaries in classification request: grade %s, %s = %i/%i', async (
    grade, countName, numerator, denominator, expected, boundary, atOrAbove,
  ) => {
    useProviderFor(grade);
    // Mock counts, not the preprocessing. 44.9 catches whole-number rounding;
    // 44.96 and 59.96 catch rounding to one decimal before truncation.
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: {
          ...createMockSentenceAnalysis(),
          num_sentences: denominator,
          num_words: denominator * 10,
          sentence_word_counts: Array(denominator).fill(10),
          [countName]: numerator,
        },
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 0,
      })
      .mockResolvedValueOnce({
        data: { complexity_score: 'slightly_complex', reasoning: 'Mock classification' },
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 0,
      });

    await evaluator.evaluate({ text: 'Test passage.', grade_level: grade });
    const messages = vi.mocked(mockProvider.generateStructured).mock.calls[1][0].messages;
    const prompt = messages.map((message) => message.content).join('\n');
    const features = JSON.parse(prompt.split('# TEXT STATISTICS\n')[1]);
    const featureName = countName.replace('num_', 'percent_');
    expect(features[featureName]).toBe(expected);
    expect(features[featureName] >= boundary).toBe(atOrAbove);
    expect(features[featureName] < boundary).toBe(!atOrAbove);
    expect(prompt.split('\n').some((line) =>
      line.includes(`\`${featureName}\``) && line.includes(`>= ${boundary}%`),
    )).toBe(true);
    // The mocked final label does not test LLM accuracy; the request's numeric
    // values and inclusive cutoff instructions are the regression contract.
  });

  describe('Error Handling', () => {
    it('should handle sentence analysis API failure', async () => {
      const testText = 'Test text here for API failure';
      const testGrade = '3';
      useProviderFor(testGrade);

      // Stage 1 fails — stage 2 should never be reached
      vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(
        new Error('API timeout')
      );

      // Should propagate the error
      await expect(evaluator.evaluate({ text: testText, grade_level: testGrade }))
        .rejects.toThrow('API timeout');

      // Provider called once (stage 1 only)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
    });

    it('should handle complexity classification API failure', async () => {
      const testText = 'Test text here for complexity failure';
      const testGrade = '5';
      useProviderFor(testGrade);

      // Stage 1 succeeds, stage 2 fails
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'stub-model',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockRejectedValueOnce(new Error('Schema validation failed'));

      // Should propagate the error
      await expect(evaluator.evaluate({ text: testText, grade_level: testGrade }))
        .rejects.toThrow('Schema validation failed');

      // Provider called twice (stage 1 completed, stage 2 failed)
      expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
    });

  });

  describe('Response Structure', () => {
    it('should return correct result structure', async () => {
      useProviderFor('5');
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'stub-model',
          usage: { inputTokens: 150, outputTokens: 100 },
          latencyMs: 600,
        })
        .mockResolvedValueOnce({
          data: {
            complexity_score: 'moderately_complex',
            reasoning: 'Detailed reasoning here',
          },
          model: 'stub-model',
          usage: { inputTokens: 250, outputTokens: 80 },
          latencyMs: 500,
        });

      const result = await evaluator.evaluate({ text: 'Test text here', grade_level: '5' });

      // Verify result structure
      expect(result).toHaveProperty('evaluator');
      expect(result).toHaveProperty('result');
      expect(result).toHaveProperty('metadata');
      expect(result).not.toHaveProperty('score');

      // Verify metadata structure
      expect(result.metadata).toHaveProperty('model');
      expect(result.metadata).toHaveProperty('processingTimeMs');

      // Verify metadata values
      expect(result.metadata.model).toBe(expectedModel('5'));
      expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
      expect(result.metadata.tokenUsage.inputTokens).toBe(400);
      expect(result.metadata.tokenUsage.outputTokens).toBe(180);
    });
  });

  // A placeholder left unsubstituted reaches the model as literal "{grade_level}"
  // and degrades the prompt silently — nothing else in the suite would notice.
  describe('Prompt substitution', () => {
    it('leaves no unsubstituted placeholder in either stage, system or user', async () => {
      useProviderFor('7');
      vi.mocked(mockProvider.generateStructured)
        .mockResolvedValueOnce({
          data: createMockSentenceAnalysis(),
          model: 'stub-model',
          usage: { inputTokens: 1, outputTokens: 1 },
          latencyMs: 1,
        })
        .mockResolvedValueOnce({
          data: { complexity_score: 'moderately_complex', reasoning: 'why' },
          model: 'stub-model',
          usage: { inputTokens: 1, outputTokens: 1 },
          latencyMs: 1,
        });

      await evaluator.evaluate({ text: 'The cat sat on the mat. It was sleeping.', grade_level: '7' });

      const sent = vi
        .mocked(mockProvider.generateStructured)
        .mock.calls.flatMap((call) => call[0].messages.map((m) => m.content))
        .join('\n');

      expect(sent).not.toMatch(/\{[a-z_]+\}/);
    });

  });
});

/**
 * The contract is two evaluators split by grade, each validated on its own model. These
 * drive the real contract, so a band wired to the other band's steps or model fails here.
 */
describe('SentenceStructureEvaluator - grade bands', () => {
  const respond = (provider: LLMProvider) =>
    vi
      .mocked(provider.generateStructured)
      .mockResolvedValueOnce({
        data: createMockSentenceAnalysis(),
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      })
      .mockResolvedValueOnce({
        data: { complexity_score: 'moderately_complex', reasoning: 'why' },
        model: 'stub-model',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      });

  const providersOf = (evaluator: SentenceStructureEvaluator) =>
    // @ts-expect-error Accessing private property for testing
    evaluator.providers as Map<string, LLMProvider>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it.each([
    ['3', 'grades_3_4', 'openai:gpt-6-luna'],
    ['7', 'grades_5_12', 'openai:gpt-5.5-2026-04-23'],
  ] as const)('grade %s runs the two %s steps on %s', async (grade, band, model) => {
    const evaluator = new SentenceStructureEvaluator({ openaiApiKey: 'k', telemetry: false });
    const providers = providersOf(evaluator);
    const used = providers.get(`sentence_analysis_${band}`)!;
    respond(used);

    const result = await evaluator.evaluate({ text: 'The cat sat. It slept.', grade_level: grade });

    // Both steps of the band share the one provider, and the other band's is never called.
    expect(providers.get(`classify_complexity_${band}`)).toBe(used);
    expect(used.label).toBe(model);
    expect(used.generateStructured).toHaveBeenCalledTimes(2);
    for (const provider of new Set(providers.values())) {
      if (provider !== used) expect(provider.generateStructured).not.toHaveBeenCalled();
    }
    expect(result.metadata.model).toBe(model);
    expect(result.result.complexity_score).toBe('moderately_complex');
  });

  it.each(['3', '7'] as const)('sends reasoning effort none and no temperature at grade %s', async (grade) => {
    const evaluator = new SentenceStructureEvaluator({ openaiApiKey: 'k', telemetry: false });
    const used = providersOf(evaluator).get(stepsFor(grade)[0].id)!;
    respond(used);

    await evaluator.evaluate({ text: 'The cat sat. It slept.', grade_level: grade });

    for (const [request] of vi.mocked(used.generateStructured).mock.calls) {
      expect(request.reasoningEffort).toBe('none');
      expect(request.temperature).toBeNull();
    }
  });

  it.each([
    { grade: '3', caps: [12000, 2000] },
    { grade: '7', caps: [12000, 2000] },
  ] as const)('sends each step its declared output cap at grade $grade', async ({ grade, caps }) => {
    // The analysis step is the one that has run away; a cap makes that fail fast.
    const evaluator = new SentenceStructureEvaluator({ openaiApiKey: 'k', telemetry: false });
    const used = providersOf(evaluator).get(stepsFor(grade)[0].id)!;
    respond(used);

    await evaluator.evaluate({ text: 'The cat sat. It slept.', grade_level: grade });

    expect(vi.mocked(used.generateStructured).mock.calls.map(([request]) => request.maxTokens)).toEqual(caps);
  });

  it('does not send the declared reasoning effort to an overriding model', async () => {
    // The value was validated on the declared model; the override is a different one,
    // and may not be a reasoning model at all.
    const evaluator = new SentenceStructureEvaluator({
      openaiApiKey: 'k',
      telemetry: false,
      modelOverride: { provider: Provider.OpenAI, model: 'gpt-other' },
    });
    const used = providersOf(evaluator).get(stepsFor('7')[0].id)!;
    respond(used);

    await evaluator.evaluate({ text: 'The cat sat. It slept.', grade_level: '7' });

    expect(used.label).toBe('openai:gpt-other');
    for (const [request] of vi.mocked(used.generateStructured).mock.calls) {
      expect(request).not.toHaveProperty('reasoningEffort');
    }
  });

  it('does not send the declared reasoning effort to an injected provider', async () => {
    const llmProvider = createMockProvider();
    respond(llmProvider);
    const evaluator = new SentenceStructureEvaluator({ llmProvider, telemetry: false });

    await evaluator.evaluate({ text: 'The cat sat. It slept.', grade_level: '3' });

    expect(llmProvider.generateStructured).toHaveBeenCalledTimes(2);
    for (const [request] of vi.mocked(llmProvider.generateStructured).mock.calls) {
      expect(request).not.toHaveProperty('reasoningEffort');
    }
  });
});

describe('Raw floor boundary behavior', () => {
  it.each([12, 13, 16, 17, 19, 22, 25, 30, 40, 45, 50, 55, 60])(
    'preserves comparisons at integer boundary %s', (boundary) => {
      for (const offset of [-0.04, 0, 0.04]) {
        const raw = boundary + offset;
        const features = { ...addEngineeredFeatures(createMockSentenceAnalysis()), avg_words_per_sentence: raw };
        const payload = JSON.parse(featuresToJSON(features, 1, true, true));
        expect(payload.avg_words_per_sentence < boundary).toBe(raw < boundary);
        expect(payload.avg_words_per_sentence >= boundary).toBe(raw >= boundary);
      }
    }
  );
});
