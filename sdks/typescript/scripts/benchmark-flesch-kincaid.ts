/**
 * Benchmark every Flesch-Kincaid implementation available to this SDK against Python
 * textstat, and rewrite the results section of `docs/flesch-kincaid.md`.
 *
 *     npm run benchmark:fk
 *
 * Ground truth is `tests/unit/features/flesch-kincaid/parity-corpus.json`, which records
 * textstat's own answers. Regenerate it with `npm run generate:fk-corpus` when the corpus
 * or textstat changes.
 */
import { readFileSync, writeFileSync } from 'node:fs';
import textReadability from 'text-readability';
import { textstat as textstatTs } from 'textstat-ts';
import readabilityScores from 'readability-scores';
import nlp from 'compromise';
import { syllable } from 'syllable';
import {
  countSentences,
  countSyllables,
  countWords,
  fleschKincaidGrade,
  roundGrade,
} from '../src/features/flesch-kincaid/index.js';

const CORPUS_PATH = new URL(
  '../tests/unit/features/flesch-kincaid/parity-corpus.json',
  import.meta.url
);
const DOC_PATH = new URL('../docs/flesch-kincaid.md', import.meta.url);

const BEGIN = '<!-- BEGIN BENCHMARK -->';
const END = '<!-- END BENCHMARK -->';

interface Case {
  group: string;
  text: string;
  words: number;
  sentences: number;
  syllables: number;
  fk: number;
  fkRounded: number;
}

interface Counts {
  words: number;
  sentences: number;
  syllables: number;
}

interface Implementation {
  name: string;
  note: string;
  /** Grade, on the same scale textstat reports (unrounded) where the library allows. */
  grade: (text: string) => number;
  /** Only reports 2dp, so it can only be judged on the rounded scale. */
  roundedOnly?: boolean;
  counts?: (text: string) => Counts;
}

function handRolledCounts(text: string): Counts {
  const doc = nlp(text);
  const terms = doc.terms();
  const words = terms.length;
  return {
    words,
    sentences: doc.sentences().length,
    syllables: (terms.out('array') as string[]).reduce((sum, word) => sum + syllable(word), 0),
  };
}

const IMPLEMENTATIONS: Implementation[] = [
  {
    name: 'this SDK (textstat port)',
    note: 'CMUdict + pyphen, ported from textstat',
    grade: fleschKincaidGrade,
    counts: (text) => ({
      words: countWords(text),
      sentences: countSentences(text),
      syllables: countSyllables(text),
    }),
  },
  {
    name: 'text-readability',
    note: 'declared by the contracts for TypeScript',
    grade: (text) => textReadability.fleschKincaidGrade(text),
    counts: (text) => ({
      words: textReadability.lexiconCount(text, true),
      sentences: textReadability.sentenceCount(text),
      syllables: textReadability.syllableCount(text),
    }),
  },
  {
    name: 'textstat-ts',
    note: 'unaffiliated port, name notwithstanding',
    grade: (text) => textstatTs.fleschKincaidGrade(text),
    counts: (text) => ({
      words: textstatTs.lexiconCount(text, true),
      sentences: textstatTs.sentenceCount(text),
      syllables: textstatTs.syllableCount(text),
    }),
  },
  {
    name: 'readability-scores',
    note: 'reports 2dp only',
    grade: (text) => readabilityScores(text)?.fleschKincaid ?? Number.NaN,
    roundedOnly: true,
    counts: (text) => {
      const scores = readabilityScores(text);
      return {
        words: scores?.wordCount ?? 0,
        sentences: scores?.sentenceCount ?? 0,
        syllables: scores?.syllableCount ?? 0,
      };
    },
  },
  {
    name: 'compromise + syllable',
    note: 'the SDK’s previous hand-rolled implementation',
    grade: (text) => {
      const { words, sentences, syllables } = handRolledCounts(text);
      const wordsPerSentence = sentences > 0 ? words / sentences : 0;
      const syllablesPerWord = words > 0 ? syllables / words : 0;
      return 0.39 * wordsPerSentence + 11.8 * syllablesPerWord - 15.59;
    },
    counts: handRolledCounts,
  },
];

function quantile(sorted: number[], q: number): number {
  if (sorted.length === 0) return 0;
  const index = Math.min(sorted.length - 1, Math.floor(q * sorted.length));
  return sorted[index];
}

interface Stats {
  n: number;
  scored: number;
  noResult: number;
  mean: number;
  median: number;
  p95: number;
  max: number;
  exact: number;
  withinHalf: number;
  withinOne: number;
}

/**
 * `errors` may contain nulls: `readability-scores` returns nothing for 10 of the inputs.
 * Those are counted and excluded rather than scored as an infinite error, which would make
 * every other statistic for that library unreadable. Percentages stay over all inputs, so
 * a library is not rewarded for declining to answer.
 */
function summarise(errors: (number | null)[]): Stats {
  const scored = errors.filter((e): e is number => e !== null);
  const sorted = [...scored].sort((a, b) => a - b);
  return {
    n: errors.length,
    scored: scored.length,
    noResult: errors.length - scored.length,
    mean: scored.reduce((a, b) => a + b, 0) / Math.max(1, scored.length),
    median: quantile(sorted, 0.5),
    p95: quantile(sorted, 0.95),
    max: sorted[sorted.length - 1] ?? 0,
    // An implementation is only a drop-in replacement if it is exact; the tolerance
    // columns say how wrong the others are in terms a reader can act on.
    exact: scored.filter((e) => e < 1e-9).length,
    withinHalf: scored.filter((e) => e <= 0.5).length,
    withinOne: scored.filter((e) => e <= 1).length,
  };
}

const corpus = JSON.parse(readFileSync(CORPUS_PATH, 'utf-8')) as {
  textstatVersion: number[];
  cases: Case[];
};

const GROUPS = [...new Set(corpus.cases.map((c) => c.group))];

function errorsFor(impl: Implementation, cases: Case[]): (number | null)[] {
  return cases.map((c) => {
    // A library that only reports 2dp is compared against textstat's 2dp value, or its
    // rounding would be scored as inaccuracy.
    const truth = impl.roundedOnly ? c.fkRounded : c.fk;
    const raw = impl.grade(c.text);
    if (!Number.isFinite(raw)) return null;
    return Math.abs((impl.roundedOnly ? roundGrade(raw) : raw) - truth);
  });
}

function pct(part: number, whole: number): string {
  return `${((100 * part) / whole).toFixed(0)}%`;
}

/**
 * Escape a fixture snippet for a markdown table cell.
 *
 * Backslashes first, then the delimiter: escaping `|` alone turns a literal `\|` in the
 * text into `\\|`, which renders as a backslash followed by an unescaped delimiter and
 * breaks the row.
 */
function tableCell(text: string): string {
  return text.replace(/\\/g, '\\\\').replace(/\|/g, '\\|');
}

function fixed(value: number): string {
  if (!Number.isFinite(value)) return 'n/a';
  return value.toFixed(4);
}

const lines: string[] = [];

lines.push(
  `_Generated by \`npm run benchmark:fk\` against textstat ${corpus.textstatVersion.join('.')}` +
    `, over ${corpus.cases.length} inputs. Do not edit by hand._`
);
lines.push('');

lines.push('### Overall');
lines.push('');
lines.push(
  '| implementation | mean abs. err | median | p95 | worst | exact | ±0.5 | ±1.0 | no result |'
);
lines.push('| --- | --- | --- | --- | --- | --- | --- | --- | --- |');
for (const impl of IMPLEMENTATIONS) {
  const s = summarise(errorsFor(impl, corpus.cases));
  lines.push(
    `| ${impl.name} | ${fixed(s.mean)} | ${fixed(s.median)} | ${fixed(s.p95)} | ` +
      `${fixed(s.max)} | ${pct(s.exact, s.n)} | ${pct(s.withinHalf, s.n)} | ` +
      `${pct(s.withinOne, s.n)} | ${s.noResult === 0 ? '—' : s.noResult} |`
  );
}
lines.push('');

lines.push('### By input class');
lines.push('');
for (const group of GROUPS) {
  const cases = corpus.cases.filter((c) => c.group === group);
  lines.push(`**${group}** (${cases.length} inputs)`);
  lines.push('');
  lines.push('| implementation | mean abs. err | worst | exact |');
  lines.push('| --- | --- | --- | --- |');
  for (const impl of IMPLEMENTATIONS) {
    const s = summarise(errorsFor(impl, cases));
    lines.push(`| ${impl.name} | ${fixed(s.mean)} | ${fixed(s.max)} | ${pct(s.exact, s.n)} |`);
  }
  lines.push('');
}

lines.push('### Where the divergence comes from');
lines.push('');
lines.push(
  'The grade is one formula over three counts, so a single table of grade error hides ' +
    'which count is wrong. Share of the corpus where each count matches textstat:'
);
lines.push('');
lines.push('| implementation | words | sentences | syllables |');
lines.push('| --- | --- | --- | --- |');
for (const impl of IMPLEMENTATIONS) {
  if (!impl.counts) continue;
  let words = 0;
  let sentences = 0;
  let syllables = 0;
  for (const c of corpus.cases) {
    const got = impl.counts(c.text);
    if (got.words === c.words) words += 1;
    if (got.sentences === c.sentences) sentences += 1;
    if (got.syllables === c.syllables) syllables += 1;
  }
  const n = corpus.cases.length;
  lines.push(
    `| ${impl.name} | ${pct(words, n)} | ${pct(sentences, n)} | ${pct(syllables, n)} |`
  );
}
lines.push('');

lines.push('### Worst cases against the declared library');
lines.push('');
lines.push(
  'The inputs where `text-readability` — the implementation the contracts name for ' +
    'TypeScript — is furthest from textstat, restricted to fixture prose so these are ' +
    'texts an evaluator would really be given:'
);
lines.push('');
lines.push('| textstat | text-readability | delta | text |');
lines.push('| --- | --- | --- | --- |');

const declared = IMPLEMENTATIONS.find((i) => i.name === 'text-readability');
if (declared) {
  const seen = new Set<string>();
  const prose = corpus.cases.filter((c) => {
    if (c.group !== 'fixture-prose' || seen.has(c.text)) return false;
    seen.add(c.text);
    return true;
  });
  const ranked = prose
    .map((c) => ({ c, got: declared.grade(c.text) }))
    .sort((a, b) => Math.abs(b.got - b.c.fk) - Math.abs(a.got - a.c.fk))
    .slice(0, 5);
  for (const { c, got } of ranked) {
    const snippet = tableCell(c.text.replace(/\s+/g, ' ').slice(0, 60));
    lines.push(
      `| ${c.fk.toFixed(2)} | ${got.toFixed(2)} | **${Math.abs(got - c.fk).toFixed(2)}** | ${snippet}… |`
    );
  }
}

const block = `${BEGIN}\n\n${lines.join('\n')}\n${END}`;
const doc = readFileSync(DOC_PATH, 'utf-8');
const start = doc.indexOf(BEGIN);
const end = doc.indexOf(END);
if (start === -1 || end === -1) {
  throw new Error(`benchmark markers not found in ${DOC_PATH.pathname}`);
}

writeFileSync(DOC_PATH, doc.slice(0, start) + block + doc.slice(end + END.length));
console.log(`wrote results for ${corpus.cases.length} inputs to docs/flesch-kincaid.md`);
