/**
 * Ports of the textstat counting functions the Flesch-Kincaid grade is built from.
 *
 * Each function mirrors one textstat backend function, so a divergence is traceable to a
 * single place rather than to "the formula".
 */

// Python's `\w` is Unicode-aware for `str` patterns; JS's is ASCII-only. Spelled out, or
// accented text keeps characters JS does not treat as word characters and the count drifts.
const WORD_CHAR = String.raw`\p{L}\p{N}_`;

const RE_ALL_PUNCTUATION = new RegExp(`[^${WORD_CHAR}\\s]`, 'gu');
const RE_PUNCTUATION_KEEP_APOSTROPHE = new RegExp(`[^${WORD_CHAR}\\s']`, 'gu');

// Likewise `\b`: JS's is ASCII-only even under the `u` flag, so a sentence starting with `ß`
// or `é` has no boundary to match and silently merges into its predecessor. This is the
// two-sided boundary definition written out.
const WORD_BOUNDARY = `(?:(?<![${WORD_CHAR}])(?=[${WORD_CHAR}])|(?<=[${WORD_CHAR}])(?![${WORD_CHAR}]))`;
const RE_SENTENCES = new RegExp(`${WORD_BOUNDARY}[^.!?]+[.!?]*`, 'gu');

const CONTRACTION_ENDINGS = String.raw`[tsd]|ve|ll|re`;
const RE_NONCONTRACTION_APOSTROPHE = new RegExp(`'(?!${CONTRACTION_ENDINGS})`, 'g');
const RE_CONTRACTION_APOSTROPHE = new RegExp(`'(?=${CONTRACTION_ENDINGS})`, 'g');

export interface ListWordsOptions {
  removePunctuation?: boolean;
  removeApostrophe?: boolean;
  lowercase?: boolean;
  splitContractions?: boolean;
  splitHyphens?: boolean;
}

/** `textstat.backend.transformations.remove_punctuation` */
export function stripPunctuation(text: string, removeApostrophe = false): string {
  if (removeApostrophe) return text.replace(RE_ALL_PUNCTUATION, '');

  return text
    .replace(RE_NONCONTRACTION_APOSTROPHE, '')
    .replace(RE_PUNCTUATION_KEEP_APOSTROPHE, '');
}

/**
 * `textstat.backend.selections.list_words`
 *
 * Defaults match textstat's: punctuation removed, apostrophes kept, case preserved,
 * contractions and hyphenated compounds left whole. So `AI-powered` becomes the single
 * token `AIpowered`, which is why it misses CMUdict and reaches the hyphenation fallback.
 */
export function listWords(text: string, options: ListWordsOptions = {}): string[] {
  const {
    removePunctuation = true,
    removeApostrophe = false,
    lowercase = false,
    splitContractions = false,
    splitHyphens = false,
  } = options;

  let out = text;
  if (splitHyphens) out = out.replace(/-/g, ' ');
  if (removePunctuation) out = stripPunctuation(out, removeApostrophe);
  if (lowercase) out = out.toLowerCase();
  if (splitContractions) out = out.replace(RE_CONTRACTION_APOSTROPHE, ' ');

  // Python's argument-less str.split() splits on runs of whitespace and drops empties.
  return out.split(/\s+/u).filter((word) => word.length > 0);
}

/** `textstat.backend.counts.count_words` */
export function countWords(text: string, options?: ListWordsOptions): number {
  return listWords(text, options).length;
}

/**
 * `textstat.backend.counts.count_sentences`
 *
 * Fragments of two words or fewer are discarded, and the result is at least 1 for any
 * non-empty text. A page of headings therefore counts far fewer sentences than a split on
 * terminal punctuation suggests — which raises words-per-sentence and so the grade.
 */
export function countSentences(text: string): number {
  if (text.length === 0) return 0;

  const sentences = text.match(RE_SENTENCES) ?? [];
  let ignored = 0;
  for (const sentence of sentences) {
    if (countWords(sentence) <= 2) ignored += 1;
  }

  return Math.max(1, sentences.length - ignored);
}
