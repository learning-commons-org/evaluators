import nlp from 'compromise';
import { syllable } from 'syllable';

/**
 * Flesch-Kincaid grade level over compromise + syllable.
 *
 * Approximates Python's `textstat.flesch_kincaid_grade()` but does not match it, and is not
 * the implementation the contract declares. One caller remains — vocabulary-complexity,
 * which is the sole entry left in PREPROCESSING_GAPS in registry-conformance.test.ts.
 */
export function calculateFleschKincaidGrade(text: string): number {
  return calculateReadabilityMetrics(text).fleschKincaidGrade;
}

/**
 * Additional readability metrics
 */
export interface ReadabilityMetrics {
  sentenceCount: number;
  wordCount: number;
  characterCount: number;
  syllableCount: number;
  avgWordsPerSentence: number;
  avgSyllablesPerWord: number;
  fleschKincaidGrade: number;
}

export function calculateReadabilityMetrics(text: string): ReadabilityMetrics {
  const doc = nlp(text);

  const sentences = doc.sentences().length;
  const terms = doc.terms();
  const words = terms.length;
  const characters = text.replace(/\s/g, '').length;

  const allWords = terms.out('array');
  const totalSyllables = allWords.reduce((sum: number, word: string) => sum + syllable(word), 0);

  const avgWordsPerSentence = sentences > 0 ? words / sentences : 0;
  const avgSyllablesPerWord = words > 0 ? totalSyllables / words : 0;
  const fkGrade = 0.39 * avgWordsPerSentence + 11.8 * avgSyllablesPerWord - 15.59;

  return {
    sentenceCount: sentences,
    wordCount: words,
    characterCount: characters,
    syllableCount: totalSyllables,
    avgWordsPerSentence,
    avgSyllablesPerWord,
    fleschKincaidGrade: Math.round(Math.max(0, fkGrade) * 100) / 100,
  };
}

/**
 * The deterministic counts the sentence-structure contract binds to `{ground_truth_counts}`.
 *
 * The prompt instructs the model to treat these as a reference rather than a constraint, so
 * the block's field names and order are part of the prompt's contract, not a display choice.
 */
export function formatGroundTruthCounts(text: string): string {
  const metrics = calculateReadabilityMetrics(text);

  return [
    `num_sentences: ${metrics.sentenceCount}`,
    `num_words: ${metrics.wordCount}`,
    `num_char: ${metrics.characterCount}`,
    `num_syllable: ${metrics.syllableCount}`,
    `flesch_kincaid_grade: ${metrics.fleschKincaidGrade}`,
  ].join('\n');
}
