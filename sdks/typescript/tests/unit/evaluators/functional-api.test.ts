import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  evaluateMeaningDirectness,
  evaluateGradeLevelAppropriateness,
  evaluateReferenceKnowledgeDemands,
  evaluateOrganizationalStructure,
  evaluatePurposeClarity,
  evaluateSentenceStructure,
  evaluateBackgroundKnowledgeDemands,
  evaluateVocabularyComplexity,
} from '../../../src/evaluators/index.js';
import type { LLMProvider } from '../../../src/providers/base.js';

/**
 * The functional wrappers are public API — every one is re-exported from the
 * package root — but nothing exercised them, so a wrapper passing the wrong
 * argument through to its evaluator would have shipped unnoticed.
 */

const mockProvider: LLMProvider = {
  label: 'google:gemini-3-flash-preview',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
};

vi.mock('../../../src/providers/index.js', () => ({
  createProvider: vi.fn(() => mockProvider),
}));

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class MockTelemetryClient {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

// Superset of every evaluator's output shape, so one stub serves all of them.
const RESPONSE = {
  data: {
    complexity_level: 'Very complex',
    complexity_score: 'very_complex',
    grade_band: '6-8',
    alternative_grade_band: '9-10',
    scaffolding_needed: 'none',
    reasoning: 'because',
    grade_context: 'above grade',
    details: { detailed_summary: [], adjustment_and_scaffolding: [], recommended_use_cases: [] },
    assumption: 'students know this',
    // Sentence Structure's second stage reports its verdict as `answer`.
    answer: 'Very Complex',
    // Sentence Structure computes engineered features from its first-stage
    // output, so every count it divides by has to be present and non-zero.
    num_sentences: 2,
    num_words: 20,
    flesch_kincaid_grade: 9.1,
    sentence_word_counts: [12, 8],
    num_simple_sentences: 1,
    num_compound_sentences: 1,
    num_complex_sentences: 0,
    num_compound_complex_sentences: 0,
    num_other_sentences: 0,
    num_independent_clauses: 2,
    num_subordinate_clauses: 1,
    num_total_clauses: 3,
    num_sentences_with_subordinate: 1,
    num_sentences_with_multiple_subordinates: 0,
    num_sentences_with_embedded_clauses: 0,
    num_prepositional_phrases: 2,
    num_participle_phrases: 0,
    num_appositive_phrases: 0,
    num_simple_transitions: 1,
    num_sophisticated_transitions: 0,
    words_in_simple_sentences: 12,
    words_in_compound_sentences: 8,
    words_in_complex_sentences: 0,
    words_in_compound_complex_sentences: 0,
    words_in_other_sentences: 0,
    num_one_concept_sentences: 1,
    num_multi_concept_sentences: 1,
    num_cleft_sentences: 0,
    max_clauses_in_any_sentence: 2,
  },
  model: 'gemini-3-flash-preview',
  usage: { inputTokens: 10, outputTokens: 5 },
  latencyMs: 1,
};

const TEXT =
  'The author sustains irony throughout the passage to critique the hypocrisy of civilized society.';
const GRADE_LEVEL = '10';
const CONFIG = {
  googleApiKey: 'k',
  openaiApiKey: 'k',
  anthropicApiKey: 'k',
  telemetry: false as const,
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(mockProvider.generateStructured).mockResolvedValue(RESPONSE);
  vi.mocked(mockProvider.generateText).mockResolvedValue({
    text: 'plain text answer',
    usage: { inputTokens: 3, outputTokens: 2 },
    latencyMs: 1,
  });
});

describe('functional API wrappers', () => {
  // Each takes (text, gradeLevel, config) and must reach the LLM with both.
  it.each([
    ['evaluateMeaningDirectness', evaluateMeaningDirectness],
    ['evaluateReferenceKnowledgeDemands', evaluateReferenceKnowledgeDemands],
    ['evaluateOrganizationalStructure', evaluateOrganizationalStructure],
    ['evaluatePurposeClarity', evaluatePurposeClarity],
    ['evaluateSentenceStructure', evaluateSentenceStructure],
    ['evaluateBackgroundKnowledgeDemands', evaluateBackgroundKnowledgeDemands],
    ['evaluateVocabularyComplexity', evaluateVocabularyComplexity],
  ])('%s forwards its inputs and returns a result', async (_name, fn) => {
    const result = await (
      fn as (i: { text: string; grade_level: string }, c: typeof CONFIG) => Promise<unknown>
    )({ text: TEXT, grade_level: GRADE_LEVEL }, CONFIG);

    expect(result).toBeDefined();
    expect(mockProvider.generateStructured).toHaveBeenCalled();

    // The prompt is where a swapped or dropped argument would actually show up.
    const prompts = vi
      .mocked(mockProvider.generateStructured)
      .mock.calls.flatMap((call) => call[0].messages.map((m) => m.content))
      .join('\n');
    expect(prompts).toContain(GRADE_LEVEL);
  });

  // Grade-free by design: it decides the grade level rather than being told one.
  it('evaluateGradeLevelAppropriateness takes no gradeLevel', async () => {
    const result = await evaluateGradeLevelAppropriateness({ text: TEXT }, CONFIG);

    expect(result.result.grade_band).toBe('6-8');
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(1);
  });

  it('propagates a validation failure rather than swallowing it', async () => {
    await expect(
      evaluateMeaningDirectness({ text: '', grade_level: GRADE_LEVEL }, CONFIG),
    ).rejects.toThrow(/empty|whitespace/i);
  });
});
