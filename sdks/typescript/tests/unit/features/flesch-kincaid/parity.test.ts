import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import {
  countSentences,
  countSyllables,
  countWords,
  fleschKincaidGrade,
  roundGrade,
  textStatistics,
} from '../../../../src/features/flesch-kincaid/index.js';

interface Case {
  text: string;
  words: number;
  sentences: number;
  syllables: number;
  fk: number;
  fkRounded: number;
}

// Located from `import.meta.url` rather than `__dirname`: the package is ESM, and
// `__dirname` only resolves here because Vitest supplies it.
const corpus = JSON.parse(
  readFileSync(new URL('./parity-corpus.json', import.meta.url), 'utf-8')
) as { textstatVersion: number[]; cases: Case[] };

const label = (text: string) => JSON.stringify(text.slice(0, 48));

describe('parity with textstat', () => {
  it('has a corpus that covers prose, edge cases and adversarial input', () => {
    // A corpus that quietly shrank would make every assertion below pass for nothing.
    expect(corpus.cases.length).toBeGreaterThan(600);
    expect(corpus.cases.some((c) => c.text === '')).toBe(true);
    expect(corpus.cases.some((c) => c.text.length > 1000)).toBe(true);
    expect(corpus.cases.some((c) => /[^\p{ASCII}]/u.test(c.text))).toBe(true);
    // `textstat.__version__` is a tuple, so this arrives as [0, 7, 13]. It is the
    // provenance of every expectation in the file and should not silently disappear.
    expect(corpus.textstatVersion.every((part) => typeof part === 'number')).toBe(true);
  });

  // Asserted per component as well as on the grade: all three counts feed one formula, so
  // two errors can cancel and a grade-only check would call that parity.
  it.each(corpus.cases.map((c, i) => ({ i, c })))('case $i counts', ({ c }) => {
    expect(countWords(c.text), `words for ${label(c.text)}`).toBe(c.words);
    expect(countSentences(c.text), `sentences for ${label(c.text)}`).toBe(c.sentences);
    expect(countSyllables(c.text), `syllables for ${label(c.text)}`).toBe(c.syllables);
  });

  it('reproduces every grade to the last bit', () => {
    // Not a tolerance: the operations run in textstat's order on the same doubles, so the
    // results are bit-identical. A tolerance here would hide a real divergence.
    const deltas = corpus.cases.map((c) => Math.abs(fleschKincaidGrade(c.text) - c.fk));

    expect(Math.max(...deltas)).toBe(0);
  });

  it('rounds as Python does', () => {
    for (const c of corpus.cases) {
      expect(roundGrade(fleschKincaidGrade(c.text)), label(c.text)).toBe(c.fkRounded);
    }
  });

  it('rounds ties the way Python does, not the way Math.round does', () => {
    // The values below are exact ties at 2dp that arise in the corpus. Python rounds half
    // to even on the decimal representation; `Math.round(v * 100) / 100` rounds half up and
    // gives 2.72, 5.81 and 18.51 instead.
    expect(roundGrade(2.715)).toBe(2.71);
    expect(roundGrade(5.805)).toBe(5.8);
    expect(roundGrade(18.505)).toBe(18.5);
  });
});

describe('textStatistics', () => {
  it('reports the components behind the grade', () => {
    const stats = textStatistics('The cat sat on the mat. It was warm and soft.');

    expect(stats).toEqual({
      words: countWords('The cat sat on the mat. It was warm and soft.'),
      sentences: 2,
      syllables: countSyllables('The cat sat on the mat. It was warm and soft.'),
      fleschKincaidGrade: fleschKincaidGrade('The cat sat on the mat. It was warm and soft.'),
    });
  });
});
