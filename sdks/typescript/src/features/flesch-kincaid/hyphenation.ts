/**
 * Port of pyphen's hyphenation, which textstat uses for words CMUdict does not carry.
 *
 * Only `positions()` is needed: textstat's syllable fallback is
 * `len(pyphen.positions(word)) + 1`.
 */

const IGNORED_PREFIXES = [
  '%',
  '#',
  'LEFTHYPHENMIN',
  'RIGHTHYPHENMIN',
  'COMPOUNDLEFTHYPHENMIN',
  'COMPOUNDRIGHTHYPHENMIN',
];

interface Pattern {
  offset: number;
  values: number[];
}

/**
 * Split a pattern into its letters and the priority values between them.
 *
 * Mirrors Python's `re.findall(r'(\d?)(\D?)', pattern)`, whose trailing empty match
 * contributes a final zero — dropping it shifts every offset by one.
 */
function parsePattern(pattern: string): { tag: string; values: number[] } {
  const tags: string[] = [];
  const values: number[] = [];

  for (const match of pattern.matchAll(/(\d?)(\D?)/g)) {
    values.push(match[1] ? Number(match[1]) : 0);
    if (match[2]) tags.push(match[2]);
  }

  return { tag: tags.join(''), values };
}

export class Hyphenator {
  private readonly patterns = new Map<string, Pattern>();
  private readonly maxlen: number;
  private readonly cache = new Map<string, number[]>();

  /** @param dictionary contents of a `hyph_*.dic` pattern file */
  constructor(dictionary: string) {
    // The first line is the encoding declaration, not a pattern.
    for (const raw of dictionary.split('\n').slice(1)) {
      let pattern = raw.trim();
      if (!pattern || IGNORED_PREFIXES.some((prefix) => pattern.startsWith(prefix))) continue;

      pattern = pattern.replace(/\^{2}([0-9a-f]{2})/g, (_, hex: string) =>
        String.fromCharCode(parseInt(hex, 16))
      );

      // A nonstandard hyphenation alternative describes how to rewrite the word at the
      // break. pyphen attaches it to the position without changing the position's numeric
      // value, and only the count of positions matters here, so it is dropped.
      if (pattern.includes('/') && pattern.includes('=')) {
        pattern = pattern.split('/', 1)[0];
      }

      const { tag, values } = parsePattern(pattern);
      if (values.length === 0 || Math.max(...values) === 0) continue;

      let start = 0;
      let end = values.length;
      while (values[start] === 0) start += 1;
      while (values[end - 1] === 0) end -= 1;

      this.patterns.set(tag, { offset: start, values: values.slice(start, end) });
    }

    this.maxlen = Math.max(...[...this.patterns.keys()].map((key) => key.length));
  }

  /**
   * Break points, as pyphen's `Pyphen.positions` reports them.
   *
   * `left`/`right` default to 2 in pyphen and textstat does not override them, so a break
   * within two characters of either end is dropped. These are pyphen's own defaults and are
   * unrelated to the file's LEFTHYPHENMIN/RIGHTHYPHENMIN headers, which pyphen ignores —
   * implementations that honour those headers instead find fewer breaks and under-count.
   */
  positions(word: string, left = 2, right = 2): number[] {
    const limit = word.length - right;
    return this.rawPositions(word).filter((index) => index >= left && index <= limit);
  }

  private rawPositions(word: string): number[] {
    const lower = word.toLowerCase();
    const cached = this.cache.get(lower);
    if (cached !== undefined) return cached;

    const pointed = `.${lower}.`;
    const references = new Array<number>(pointed.length + 1).fill(0);

    for (let i = 0; i < pointed.length - 1; i += 1) {
      const stop = Math.min(i + this.maxlen, pointed.length) + 1;
      for (let j = i + 1; j < stop; j += 1) {
        const pattern = this.patterns.get(pointed.slice(i, j));
        if (!pattern) continue;

        for (let k = 0; k < pattern.values.length; k += 1) {
          const at = i + pattern.offset + k;
          if (at < references.length) {
            references[at] = Math.max(pattern.values[k], references[at]);
          }
        }
      }
    }

    const points: number[] = [];
    references.forEach((reference, index) => {
      if (reference % 2) points.push(index - 1);
    });

    this.cache.set(lower, points);
    return points;
  }
}
