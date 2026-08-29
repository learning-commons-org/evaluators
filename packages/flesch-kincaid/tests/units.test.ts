import { describe, expect, it } from 'vitest';
import {
  countSentences,
  countSyllables,
  countWordSyllables,
  countWords,
  fleschKincaidGrade,
  Hyphenator,
  listWords,
  stripPunctuation,
} from '../src/index.js';
import { HYPHENATION_PATTERNS } from '../src/data/hyphenation-patterns.js';

describe('listWords', () => {
  it('keeps apostrophes but drops other punctuation, as textstat does', () => {
    expect(listWords("Don't stop; it's fine!")).toEqual(["Don't", 'stop', "it's", 'fine']);
  });

  it('drops an apostrophe that is not a contraction', () => {
    // `'cause` is not in the contraction-endings set, so its apostrophe goes.
    expect(listWords("believin' 'cause")).toEqual(['believin', 'cause']);
  });

  it('joins a hyphenated compound into one token', () => {
    // This is why `AI-powered` misses CMUdict and reaches the hyphenation fallback.
    expect(listWords('AI-powered co-operative')).toEqual(['AIpowered', 'cooperative']);
  });

  it('splits hyphens when asked', () => {
    expect(listWords('AI-powered', { splitHyphens: true })).toEqual(['AI', 'powered']);
  });

  it('treats non-ASCII letters as word characters', () => {
    expect(listWords('naïve café Zürich ß')).toEqual(['naïve', 'café', 'Zürich', 'ß']);
  });

  it('splits on runs of any whitespace', () => {
    expect(listWords('a  b\tc\nd\r\ne')).toEqual(['a', 'b', 'c', 'd', 'e']);
  });
});

describe('stripPunctuation', () => {
  it('removes every mark when apostrophes are not spared', () => {
    expect(stripPunctuation("it's, fine!", true)).toBe('its fine');
  });
});

describe('countSentences', () => {
  it('is 0 only for the empty string', () => {
    expect(countSentences('')).toBe(0);
    expect(countSentences(' ')).toBe(1);
  });

  it('discards fragments of two words or fewer', () => {
    // "Hi." is one word, so it is ignored; the floor of 1 keeps the result usable.
    expect(countSentences('Hi. Hi. Hi.')).toBe(1);
    expect(countSentences('One two three. Four five six.')).toBe(2);
  });

  it('counts a sentence that begins with a non-ASCII letter', () => {
    // JS's `\b` is ASCII-only, so without an explicit Unicode boundary this merges into one.
    expect(countSentences('ßeta one two three. Alpha two three four.')).toBe(2);
  });

  it('counts text with no terminal punctuation as one sentence', () => {
    expect(countSentences('No terminal punctuation here')).toBe(1);
  });
});

describe('countSyllables', () => {
  it('reads known words from CMUdict', () => {
    expect(countWordSyllables('about')).toBe(2);
    expect(countWordSyllables('mitochondria')).toBe(5);
  });

  it('is case-insensitive', () => {
    expect(countWordSyllables('MITOCHONDRIA')).toBe(countWordSyllables('mitochondria'));
  });

  it('falls back to hyphenation for words CMUdict does not carry', () => {
    // Not a real word, so it cannot come from the dictionary.
    expect(countWordSyllables('aipowered')).toBe(2);
  });

  it('is 0 for empty text', () => {
    expect(countSyllables('')).toBe(0);
  });
});

describe('Hyphenator', () => {
  const hyphenator = new Hyphenator(HYPHENATION_PATTERNS);

  it('matches pyphen positions', () => {
    expect(hyphenator.positions('hyphenation')).toEqual([2, 6]);
    expect(hyphenator.positions('computer')).toEqual([3, 6]);
    expect(hyphenator.positions('table')).toEqual([2]);
    expect(hyphenator.positions('dot')).toEqual([]);
  });

  it('drops breaks within two characters of either end', () => {
    // pyphen's raw pass finds a break at index 0 for "computer"; its left/right defaults
    // remove it. Honouring the file's LEFTHYPHENMIN instead would give a different answer.
    expect(hyphenator.positions('computer')).not.toContain(0);
  });
});

describe('fleschKincaidGrade', () => {
  it('is 0 when there is nothing to measure', () => {
    expect(fleschKincaidGrade('')).toBe(0);
    expect(fleschKincaidGrade('...')).toBe(0);
  });

  it('never returns a negative grade for empty-ish input', () => {
    // textstat's own guard: the formula's -15.59 constant would otherwise dominate.
    expect(fleschKincaidGrade(' ')).toBe(0);
  });

  it('rises with sentence length and syllable weight', () => {
    const simple = fleschKincaidGrade('The cat sat. The dog ran. The bird flew.');
    const complex = fleschKincaidGrade(
      'The photosynthetic mitochondria facilitated extraordinarily complicated metabolic ' +
        'transformations throughout the organism.'
    );

    expect(complex).toBeGreaterThan(simple);
  });

  it('counts words and sentences consistently with its own components', () => {
    const text = 'One two three four. Five six seven eight nine.';
    const expected =
      0.39 * (countWords(text) / countSentences(text)) +
      11.8 * (countSyllables(text) / countWords(text)) -
      15.59;

    expect(fleschKincaidGrade(text)).toBe(expected);
  });
});
