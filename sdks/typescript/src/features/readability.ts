import nlp from 'compromise';
import { syllable } from 'syllable';

/**
 * Calculate Flesch-Kincaid Grade Level
 * Equivalent to Python's textstat.flesch_kincaid_grade()
 */
export function calculateFleschKincaidGrade(text: string): number {
  const doc = nlp(text);

  const sentences = doc.sentences().length;
  const words = doc.terms().length;

  if (sentences === 0 || words === 0) {
    return 0;
  }

  // Count syllables for all words
  const allWords = doc.terms().out('array');
  const totalSyllables = allWords.reduce((sum: number, word: string) => {
    return sum + syllable(word);
  }, 0);

  // Flesch-Kincaid formula
  const avgWordsPerSentence = words / sentences;
  const avgSyllablesPerWord = totalSyllables / words;

  const fkGrade = 0.39 * avgWordsPerSentence + 11.8 * avgSyllablesPerWord - 15.59;

  return Math.round(fkGrade * 100) / 100; // Round to 2 decimal places
}

/**
 * Additional readability metrics
 */
export function calculateReadabilityMetrics(text: string) {
  const doc = nlp(text);

  const sentences = doc.sentences().length;
  const words = doc.terms().length;
  const characters = text.replace(/\s/g, '').length;

  const allWords = doc.terms().out('array');
  const totalSyllables = allWords.reduce((sum: number, word: string) => sum + syllable(word), 0);

  return {
    sentenceCount: sentences,
    wordCount: words,
    characterCount: characters,
    syllableCount: totalSyllables,
    avgWordsPerSentence: sentences > 0 ? words / sentences : 0,
    avgSyllablesPerWord: words > 0 ? totalSyllables / words : 0,
    fleschKincaidGrade: calculateFleschKincaidGrade(text),
  };
}
