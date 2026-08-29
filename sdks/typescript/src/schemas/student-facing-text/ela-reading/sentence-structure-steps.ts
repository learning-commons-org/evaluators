/**
 * Sentence Structure's intermediate types.
 *
 * Its final output is generated from `output_schema.json` in the sibling module. These are
 * the pieces the contract does not describe: the first step's analysis, and the features
 * computed from it in TypeScript before the second step is asked to classify.
 */
import { z } from 'zod';

/**
 * Stage 1: Detailed sentence analysis output (40+ metrics)
 * Ported from Python SentenceAnalysesEvaluatorOutput
 */
export const SentenceAnalysisSchema = z.object({
  reasoning: z.string().describe('Step-by-step reasoning for the analysis'),

  // Foundational
  num_sentences: z.number().int().describe('Total number of sentences in the text'),
  num_words: z.number().int().describe('Total number of words in the text'),
  flesch_kincaid_grade: z.number().describe('Flesch-Kincaid Grade Level number'),

  // Sentence Type
  num_simple_sentences: z.number().int().describe('Number of simple sentences'),
  num_compound_sentences: z.number().int().describe('Number of compound sentences'),
  num_complex_sentences: z.number().int().describe('Number of complex sentences'),
  num_compound_complex_sentences: z.number().int().describe('Number of compound-complex sentences'),
  num_other_sentences: z.number().int().describe('Number of other sentence types'),

  // Subordination
  num_independent_clauses: z.number().int(),
  num_subordinate_clauses: z.number().int(),
  num_total_clauses: z.number().int(),
  num_sentences_with_subordinate: z.number().int(),
  num_sentences_with_multiple_subordinates: z.number().int(),
  num_sentences_with_embedded_clauses: z.number().int(),

  // Informational Phrases
  num_prepositional_phrases: z.number().int(),
  num_participle_phrases: z.number().int(),
  num_appositive_phrases: z.number().int(),

  // Cohesion
  num_simple_transitions: z.number().int(),
  num_sophisticated_transitions: z.number().int(),

  // Sentence Type Density
  words_in_simple_sentences: z.number().int(),
  words_in_compound_sentences: z.number().int(),
  words_in_complex_sentences: z.number().int(),
  words_in_compound_complex_sentences: z.number().int(),
  words_in_other_sentences: z.number().int(),

  // Additional Features
  sentence_word_counts: z.array(z.number().int()),
  num_one_concept_sentences: z.number().int(),
  num_multi_concept_sentences: z.number().int(),
  num_cleft_sentences: z.number().int(),
  max_clauses_in_any_sentence: z.number().int(),

  // Grades 5-12 specific
  num_compound: z.number().int().describe('Number of compound sentences'),
  num_basic_complex: z.number().int().describe('Number of basic complex sentences'),
  num_advanced_complex: z.number().int().describe('Number of advanced complex sentences'),
  percentage_simple: z.number().describe('Percentage of simple sentences'),
  percentage_compound: z.number().describe('Percentage of compound sentences'),
  percentage_basic_complex: z.number().describe('Percentage of basic complex sentences'),
  percentage_advanced_complex: z.number().describe('Percentage of advanced complex sentences'),
});

export type SentenceAnalysis = z.infer<typeof SentenceAnalysisSchema>;


/**
 * Engineered features computed from sentence analysis
 * These are calculated in TypeScript, not requested from LLM
 */
export interface SentenceFeatures extends SentenceAnalysis {
  // Foundational & Distributional
  avg_words_per_sentence: number;
  sentence_length_variation: number;
  percent_short_sentences: number;
  percent_medium_sentences: number;
  percent_long_sentences: number;
  percent_very_long_sentences: number;

  // Sentence Structure (Grammatical Type)
  percent_simple_sentences: number;
  percent_compound_sentences: number;
  percent_complex_sentences: number;
  percent_compound_complex_sentences: number;
  percent_other_sentences: number;

  // Word Distribution
  percent_words_in_simple_sentences: number;
  percent_words_in_complex_sentences: number;
  percent_words_in_compound_sentences: number;
  percent_words_in_compound_complex_sentences: number;
  percent_words_in_other_sentences: number;

  // Clausal & Subordination
  avg_subordinates_per_sentence: number;
  avg_clauses_per_sentence: number;
  percent_sentences_with_subordinate: number;
  percent_sentences_with_multiple_subordinates: number;
  percent_sentences_with_embedded_clauses: number;

  // Phrase Density
  prep_phrase_density: number;
  participle_phrase_density: number;
  appositive_phrase_density: number;

  // Cohesion & Transitions
  avg_transitions_per_sentence: number;
  percent_sophisticated_transitions: number;

  // Conceptual & Other
  percent_sentences_w_one_concept: number;
  percent_sentences_w_multi_concept: number;
  percent_cleft_sentences: number;
}
