import { SYLLABLE_TABLE } from './data/syllables.js';
import { HYPHENATION_PATTERNS } from './data/hyphenation-patterns.js';
import { Hyphenator } from './hyphenation.js';
import { listWords } from './counts.js';

let table: Map<string, number> | undefined;
let hyphenator: Hyphenator | undefined;

// Both tables are built on first use, not at import: a caller that never asks for a
// syllable count should not pay to parse 123,455 words.
function getTable(): Map<string, number> {
  if (table === undefined) {
    table = new Map();
    for (const line of SYLLABLE_TABLE.split('\n')) {
      const tab = line.indexOf('\t');
      const count = Number(line.slice(0, tab));
      for (const word of line.slice(tab + 1).split(' ')) table.set(word, count);
    }
  }
  return table;
}

function getHyphenator(): Hyphenator {
  hyphenator ??= new Hyphenator(HYPHENATION_PATTERNS);
  return hyphenator;
}

/**
 * Syllables in one word, by the two sources textstat consults in order: CMUdict first,
 * hyphenation for anything it does not carry.
 *
 * The word is expected to be a token from {@link listWords} — punctuation already stripped.
 */
export function countWordSyllables(word: string): number {
  const lower = word.toLowerCase();
  const known = getTable().get(lower);
  if (known !== undefined) return known;
  return getHyphenator().positions(lower).length + 1;
}

/** `textstat.backend.counts.count_syllables` */
export function countSyllables(text: string): number {
  if (!text) return 0;

  let total = 0;
  for (const word of listWords(text, { lowercase: true })) {
    total += countWordSyllables(word);
  }
  return total;
}
