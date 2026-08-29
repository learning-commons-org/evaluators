#!/usr/bin/env python3
"""Record textstat's answers for a corpus, so the parity tests need no Python to run.

    pip install textstat
    python scripts/generate-parity-corpus.py

The corpus is deliberately three things at once:

* every fixture text in `evals/` — the prose this package actually has to get right
* hand-written edge cases — empty input, punctuation only, contractions, hyphenation,
  accents, digits, fragments short enough for textstat's <=2-word rule to discard
* seeded random token soup — words, punctuation and non-ASCII interleaved, which is what
  surfaced the ASCII-only `\\b` divergence that clean prose never exercises
"""

from __future__ import annotations

import json
import random
from pathlib import Path

import textstat
from textstat.backend.counts._count_sentences import count_sentences
from textstat.backend.counts._count_syllables import count_syllables
from textstat.backend.counts._count_words import count_words

HERE = Path(__file__).resolve().parent
EVALS = HERE.parent.parent.parent / 'evals'
OUT = HERE.parent / 'tests' / 'parity-corpus.json'

VOCAB = (
    "the quick brown fox jumps over a lazy dog photosynthesis mitochondria naïve café "
    "résumé Zürich AI-powered co-operative well-being state-of-the-art isn't don't "
    "they've we'll you're she'd it's MRI SLS NASA 1969 250,000 3.14 §12 hello"
).split()

PUNCT = list('.!?,;:—–-()[]{}"\'/\\|@#$%^&*_+=<>~`')
WEIRD = ['🎉', '©', '¶', ' ', ' ', '\t', '\n', '\r\n', '  ', 'ß', 'æ', 'ø', 'ñ']

EDGE = [
    '',
    ' ',
    '.',
    '!!!',
    '...',
    'Hi.',
    'Hi there.',
    'Hi there friend.',
    'One two. Three four five six.',
    "Don't stop believin'. It's a hard-won lesson, isn't it?",
    'Well-being is co-operative; re-enter the state-of-the-art co-op.',
    'The naïve café owner résuméd his rôle in Zürich.',
    'In 1969, 3 of 4 crews flew 250,000 miles.',
    'A' * 200,
    'Supercalifragilisticexpialidocious antitotalitarianism.',
    'a b c d e f g h i j k l m n o p',
    'No terminal punctuation here',
    'Multiple   spaces\tand\nnewlines\r\nbetween words.',
    'MRI, SLS, NASA, and AI-powered tools.',
    'Ellipsis... then more? Yes! Indeed.',
    '"Quoted speech," she said. \'Single quotes\' too.',
    'Numbers only: 1 2 3 4 5 6 7 8 9 10.',
    'Emoji 🎉 and symbols © § ¶ in prose that continues onward.',
    "ß it's jumps – ! ß mitochondria MRI + you're",
]


def fixture_texts() -> list[str]:
    texts = []
    for path in sorted(EVALS.rglob('fixtures.json')):
        for case in json.loads(path.read_text()):
            if not isinstance(case, dict):
                continue
            inputs = case.get('input', case)
            for key in ('text', 'student_text', 'feedback_text'):
                value = inputs.get(key)
                if isinstance(value, str) and value.strip():
                    texts.append(value)
    return texts


def random_texts() -> list[str]:
    random.seed(1234)
    texts = []
    for _ in range(400):
        parts = []
        for _ in range(random.randint(0, 40)):
            roll = random.random()
            if roll < 0.62:
                parts.append(random.choice(VOCAB))
            elif roll < 0.85:
                parts.append(random.choice(PUNCT))
            else:
                parts.append(random.choice(WEIRD))
        texts.append(' '.join(parts))
    for _ in range(150):
        texts.append(
            ''.join(random.choice(VOCAB + PUNCT + WEIRD) for _ in range(random.randint(1, 25)))
        )
    return texts


def main() -> None:
    texts = fixture_texts() + EDGE + random_texts()

    records = [
        {
            'text': text,
            'words': count_words(text),
            'sentences': count_sentences(text),
            'syllables': count_syllables(text, 'en_US'),
            'fk': textstat.flesch_kincaid_grade(text),
            'fkRounded': round(textstat.flesch_kincaid_grade(text), 2),
        }
        for text in texts
    ]

    OUT.write_text(json.dumps({'textstatVersion': textstat.__version__, 'cases': records}))
    print(f'cases: {len(records)} -> {OUT}')


if __name__ == '__main__':
    main()
