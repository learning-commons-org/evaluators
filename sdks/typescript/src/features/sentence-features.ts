import type { SentenceAnalysis, SentenceFeatures } from '../schemas/student-facing-text/ela-reading/sentence-structure-steps.js';

/**
 * Safe division helper (avoids division by zero)
 */
function safeDivision(numerator: number, denominator: number): number {
  return denominator === 0 ? 0 : numerator / denominator;
}

/**
 * Calculate standard deviation of an array of numbers
 */
function standardDeviation(values: number[]): number {
  if (values.length <= 1) return 0;

  const mean = values.reduce((sum, val) => sum + val, 0) / values.length;
  const squaredDiffs = values.map((val) => Math.pow(val - mean, 2));
  const variance = squaredDiffs.reduce((sum, val) => sum + val, 0) / values.length;

  return Math.sqrt(variance);
}

/**
 * Categorize sentence lengths into short/medium/long/very long
 */
function categorizeSentenceLengths(wordCounts: number[]) {
  if (!wordCounts || wordCounts.length === 0) {
    return {
      percent_short_sentences: 0,
      percent_medium_sentences: 0,
      percent_long_sentences: 0,
      percent_very_long_sentences: 0,
    };
  }

  let short = 0,
    medium = 0,
    long = 0,
    veryLong = 0;

  for (const count of wordCounts) {
    if (count <= 10) short++;
    else if (count <= 20) medium++;
    else if (count <= 30) long++;
    else veryLong++;
  }

  const total = wordCounts.length;

  return {
    percent_short_sentences: (short / total) * 100,
    percent_medium_sentences: (medium / total) * 100,
    percent_long_sentences: (long / total) * 100,
    percent_very_long_sentences: (veryLong / total) * 100,
  };
}

/**
 * Add engineered features to sentence analysis output
 * Ported from Python add_engineered_features function
 */
export function addEngineeredFeatures(analysis: SentenceAnalysis): SentenceFeatures {
  const numSentences = analysis.num_sentences;
  const numWords = analysis.num_words;

  // Foundational Metrics
  const avg_words_per_sentence = safeDivision(numWords, numSentences);
  const sentence_length_variation = standardDeviation(analysis.sentence_word_counts);
  const lengthCategories = categorizeSentenceLengths(analysis.sentence_word_counts);

  // Sentence Structure Percentages
  const percent_simple_sentences = safeDivision(analysis.num_simple_sentences, numSentences) * 100;
  const percent_compound_sentences =
    safeDivision(analysis.num_compound_sentences, numSentences) * 100;
  const percent_complex_sentences = safeDivision(analysis.num_complex_sentences, numSentences) * 100;
  const percent_compound_complex_sentences =
    safeDivision(analysis.num_compound_complex_sentences, numSentences) * 100;
  const percent_other_sentences = safeDivision(analysis.num_other_sentences, numSentences) * 100;

  // Word Distribution Percentages
  const percent_words_in_simple_sentences =
    safeDivision(analysis.words_in_simple_sentences, numWords) * 100;
  const percent_words_in_compound_sentences =
    safeDivision(analysis.words_in_compound_sentences, numWords) * 100;
  const percent_words_in_complex_sentences =
    safeDivision(analysis.words_in_complex_sentences, numWords) * 100;
  const percent_words_in_compound_complex_sentences =
    safeDivision(analysis.words_in_compound_complex_sentences, numWords) * 100;
  const percent_words_in_other_sentences =
    safeDivision(analysis.words_in_other_sentences, numWords) * 100;

  // Subordination and Clausal Complexity
  const avg_subordinates_per_sentence = safeDivision(analysis.num_subordinate_clauses, numSentences);
  const avg_clauses_per_sentence = safeDivision(analysis.num_total_clauses, numSentences);
  const percent_sentences_with_subordinate =
    safeDivision(analysis.num_sentences_with_subordinate, numSentences) * 100;
  const percent_sentences_with_multiple_subordinates =
    safeDivision(analysis.num_sentences_with_multiple_subordinates, numSentences) * 100;
  const percent_sentences_with_embedded_clauses =
    safeDivision(analysis.num_sentences_with_embedded_clauses, numSentences) * 100;

  // Phrase Density (per 100 words)
  const prep_phrase_density = safeDivision(analysis.num_prepositional_phrases, numWords) * 100;
  const participle_phrase_density = safeDivision(analysis.num_participle_phrases, numWords) * 100;
  const appositive_phrase_density = safeDivision(analysis.num_appositive_phrases, numWords) * 100;

  // Cohesion and Transitions
  const total_transitions = analysis.num_simple_transitions + analysis.num_sophisticated_transitions;
  const avg_transitions_per_sentence = safeDivision(total_transitions, numSentences);
  const percent_sophisticated_transitions =
    safeDivision(analysis.num_sophisticated_transitions, total_transitions) * 100;

  // Conceptual & Other
  const percent_sentences_w_one_concept =
    safeDivision(analysis.num_one_concept_sentences, numSentences) * 100;
  const percent_sentences_w_multi_concept =
    safeDivision(analysis.num_multi_concept_sentences, numSentences) * 100;
  const percent_cleft_sentences = safeDivision(analysis.num_cleft_sentences, numSentences) * 100;

  return {
    ...analysis,
    avg_words_per_sentence,
    sentence_length_variation,
    ...lengthCategories,
    percent_simple_sentences,
    percent_compound_sentences,
    percent_complex_sentences,
    percent_compound_complex_sentences,
    percent_other_sentences,
    percent_words_in_simple_sentences,
    percent_words_in_compound_sentences,
    percent_words_in_complex_sentences,
    percent_words_in_compound_complex_sentences,
    percent_words_in_other_sentences,
    avg_subordinates_per_sentence,
    avg_clauses_per_sentence,
    percent_sentences_with_subordinate,
    percent_sentences_with_multiple_subordinates,
    percent_sentences_with_embedded_clauses,
    prep_phrase_density,
    participle_phrase_density,
    appositive_phrase_density,
    avg_transitions_per_sentence,
    percent_sophisticated_transitions,
    percent_sentences_w_one_concept,
    percent_sentences_w_multi_concept,
    percent_cleft_sentences,
  };
}

/**
 * Feature columns used for complexity classification
 * Must match the order and names from Python FEATURE_COLS
 */
export const FEATURE_COLS = [
  // Foundational & Distributional
  'avg_words_per_sentence',
  'sentence_length_variation',
  'percent_short_sentences',
  'percent_medium_sentences',
  'percent_long_sentences',
  'percent_very_long_sentences',
  'flesch_kincaid_grade',
  // Sentence Structure (Grammatical Type)
  'percent_simple_sentences',
  'percent_compound_sentences',
  'percent_complex_sentences',
  'percent_compound_complex_sentences',
  'percent_other_sentences',
  // Word Distribution
  'percent_words_in_simple_sentences',
  'percent_words_in_complex_sentences',
  'percent_words_in_compound_sentences',
  'percent_words_in_compound_complex_sentences',
  'percent_words_in_other_sentences',
  // Clausal & Subordination
  'avg_subordinates_per_sentence',
  'avg_clauses_per_sentence',
  'percent_sentences_with_subordinate',
  'percent_sentences_with_multiple_subordinates',
  'percent_sentences_with_embedded_clauses',
  // Phrase Density
  'prep_phrase_density',
  'participle_phrase_density',
  'appositive_phrase_density',
  // Cohesion & Transitions
  'avg_transitions_per_sentence',
  'percent_sophisticated_transitions',
  // Conceptual & Other
  'percent_sentences_w_one_concept',
  'percent_sentences_w_multi_concept',
  'percent_cleft_sentences',
  'max_clauses_in_any_sentence',
  // Grades 5-12
  'num_sentences',
  'num_simple_sentences',
  'num_compound',
  'num_basic_complex',
  'num_advanced_complex',
  'percentage_simple',
  'percentage_compound',
  'percentage_basic_complex',
  'percentage_advanced_complex',
] as const;

/**
 * Convert sentence features to JSON string for LLM prompt
 * Ported from Python row_to_features_json
 */
export function featuresToJSON(
  features: SentenceFeatures,
  decimals = 1,
  castToInt = true
): string {
  const payload: Record<string, number | null> = {};

  for (const col of FEATURE_COLS) {
    const value = features[col as keyof SentenceFeatures];
    if (typeof value === 'number') {
      const rounded = Math.round(value * Math.pow(10, decimals)) / Math.pow(10, decimals);
      payload[col] = castToInt ? Math.round(rounded) : rounded;
    } else {
      payload[col] = null;
    }
  }

  return JSON.stringify(payload, null, 2);
}
