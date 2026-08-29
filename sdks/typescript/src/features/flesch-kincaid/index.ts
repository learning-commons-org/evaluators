import { countSentences, countWords } from './counts.js';
import { countSyllables } from './syllables.js';

export {
  countSentences,
  countWords,
  listWords,
  stripPunctuation,
  type ListWordsOptions,
} from './counts.js';
export { countSyllables, countWordSyllables } from './syllables.js';
export { Hyphenator } from './hyphenation.js';

/**
 * Flesch-Kincaid Grade Level, matching Python `textstat.flesch_kincaid_grade` exactly.
 *
 * Unrounded, as textstat returns it — textstat's own rounding is off by default. Use
 * {@link roundGrade} for the 2dp value the evaluator contracts specify.
 *
 * See `docs/flesch-kincaid-parity.md` for how this is verified and what it cost to match.
 */
export function fleschKincaidGrade(text: string): number {
  const words = countWords(text);
  const sentences = countSentences(text);

  const wordsPerSentence = sentences === 0 ? 0 : words / sentences;
  const syllablesPerWord = words === 0 ? 0 : countSyllables(text) / words;

  // textstat returns 0.0 rather than a negative grade when either term is absent.
  if (wordsPerSentence === 0 || syllablesPerWord === 0) return 0;

  return 0.39 * wordsPerSentence + 11.8 * syllablesPerWord - 15.59;
}

/**
 * Round as Python's `round()` does, which is what the contracts' "rounded to 2dp" means.
 *
 * `Math.round(value * 100) / 100` disagrees on exact ties — Python gives 2.71 for 2.715,
 * JS gives 2.72 — because Python rounds half to even on the decimal representation.
 * `toFixed` matches it on every value in this package's parity corpus.
 */
export function roundGrade(value: number, digits = 2): number {
  return Number(value.toFixed(digits));
}

export interface TextStatistics {
  words: number;
  sentences: number;
  syllables: number;
  fleschKincaidGrade: number;
}

/**
 * Every count behind the grade, for callers that report the components too — the
 * sentence-structure evaluator passes them to the model as ground truth.
 */
export function textStatistics(text: string): TextStatistics {
  return {
    words: countWords(text),
    sentences: countSentences(text),
    syllables: countSyllables(text),
    fleschKincaidGrade: fleschKincaidGrade(text),
  };
}
