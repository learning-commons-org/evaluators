# @learning-commons/flesch-kincaid

Flesch-Kincaid Grade Level for JavaScript that returns **the same number as Python's
[`textstat`](https://pypi.org/project/textstat/)**, to the last bit.

```ts
import { fleschKincaidGrade, roundGrade } from '@learning-commons/flesch-kincaid';

roundGrade(fleschKincaidGrade('The cat sat on the mat. It was warm and soft.'));
// 0.53 — the same value textstat.flesch_kincaid_grade() gives, rounded as Python rounds
```

## Why this exists

The evaluator contracts in this repository bind a precomputed `fk_score` into the prompt.
Python computes it with `textstat`; JavaScript had no library that agrees with it. Measured
against textstat over the 100 fixture texts in `evals/`:

| implementation | mean abs. error | worst | exact |
| --- | --- | --- | --- |
| **this package** | **0.0000** | **0.0000** | **100/100** |
| `text-readability` | 1.0315 | 8.9395 | 0/100 |
| `compromise` + `syllable` | 0.5392 | 6.5540 | 3/100 |

A worst case of 8.94 grade levels is not a rounding difference — it is a different answer to
"what grade is this text?", reaching the model as fact. Nothing else on npm gets closer,
because every JS option counts syllables heuristically while textstat looks them up.

## What parity requires

Four things, none of which a general-purpose readability library does:

1. **CMUdict, and the right one.** textstat loads NLTK's `cmudict` corpus (123,455 entries)
   and counts phones ending in a stress digit. The npm `cmu-pronouncing-dictionary` package
   is a *different* corpus (135,155 entries) and disagrees on real words — `nov` is 3
   syllables in one and 1 in the other.
2. **pyphen's hyphenation for the rest.** About 3% of tokens in our corpus miss CMUdict —
   numbers, names, typos, and hyphenated compounds, which textstat joins into one token
   (`AI-powered` → `AIpowered`). textstat counts their syllables as
   `len(pyphen.positions(word)) + 1`.
   Crucially pyphen *ignores* the `LEFTHYPHENMIN`/`RIGHTHYPHENMIN` headers in its own
   pattern file and applies `left=2, right=2` instead. Libraries that honour the headers
   find fewer break points and under-count.
3. **textstat's sentence rule.** Sentences are `\b[^.!?]+[.!?]*`, and any fragment of two
   words or fewer is discarded. A page of headings counts far fewer sentences than a split
   on terminal punctuation suggests, which raises words-per-sentence and so the grade.
4. **Unicode-aware regexes.** Python's `\w` and `\b` are Unicode-aware for `str` patterns;
   JavaScript's are ASCII-only even under the `u` flag. A sentence beginning with `ß` or `é`
   has no `\b` for JS to match and silently merges into the one before it.

## API

| export | notes |
| --- | --- |
| `fleschKincaidGrade(text)` | the grade, unrounded, as textstat returns it |
| `roundGrade(value, digits = 2)` | rounds as Python's `round()` does |
| `textStatistics(text)` | words, sentences, syllables and the grade together |
| `countWords`, `countSentences`, `countSyllables` | the individual counts |
| `countWordSyllables(word)` | one word, via CMUdict then hyphenation |
| `listWords`, `stripPunctuation` | textstat's tokenisation, exposed for callers that need it |
| `Hyphenator` | the pyphen port, if you need break points rather than counts |

### Rounding

`roundGrade` is not decoration. Python's `round()` rounds half to even on the decimal
representation, so `round(2.715, 2)` is `2.71`; `Math.round(2.715 * 100) / 100` is `2.72`.
Ties are rare but real — 7 of the 4,027 values measured while building this package.

## Scope

Flesch-Kincaid only, plus the counts it is built from. This is not a textstat port: there is
no Flesch Reading Ease, Gunning Fog, SMOG, Dale-Chall or Coleman-Liau, and no language other
than `en_US`. Adding one means proving parity for it the same way.

## Data and regeneration

Two generated modules under `src/data/`, checked in so the package needs no Python at
install time:

- `syllables.ts` — syllable count per CMUdict word (~1.0 MB)
- `hyphenation-patterns.ts` — pyphen's `hyph_en_US.dic`, verbatim (~120 KB)

Both are parsed lazily on first use. Regenerate after upgrading textstat, NLTK's cmudict, or
pyphen, then re-run the tests:

```bash
pip install textstat pyphen
npm run generate:data
python3 scripts/generate-parity-corpus.py
npm test
```

## Tests

`tests/parity-corpus.json` holds textstat's own answers for 674 texts, so the suite runs
without Python. It is three corpora at once: every fixture text in `evals/`, hand-written
edge cases (empty, punctuation-only, contractions, accents, digits, two-word fragments), and
seeded random token soup — which is what caught the ASCII `\b` divergence that clean prose
never exercised.

Counts are asserted per component as well as on the grade, since three counts feed one
formula and two errors can cancel.
