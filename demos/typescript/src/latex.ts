import { replace } from 'unicodeit';

// unicodeit converts LaTeX commands (\alpha, \times, x^2, y_1, …) to Unicode
// but leaves math delimiters, \frac{a}{b}, and Markdown emphasis untouched,
// so those are handled here before delegating to it.

const VULGAR_FRACTIONS: Record<string, string> = {
  '1/2': '½',
  '1/3': '⅓',
  '2/3': '⅔',
  '1/4': '¼',
  '3/4': '¾',
  '1/5': '⅕',
  '2/5': '⅖',
  '3/5': '⅗',
  '4/5': '⅘',
  '1/6': '⅙',
  '5/6': '⅚',
  '1/7': '⅐',
  '1/8': '⅛',
  '3/8': '⅜',
  '5/8': '⅝',
  '7/8': '⅞',
  '1/9': '⅑',
  '1/10': '⅒',
};

// Commands unicodeit doesn't know (or maps to the wrong glyph): \Box is the
// hollow "unknown value" placeholder in CCSS descriptions ($5 = \Box ÷ 3$).
const EXTRA_SYMBOLS: [RegExp, string][] = [[/\\Box\b/g, '□']];

// CASE standard descriptions wrap examples in Markdown emphasis
// ("*For example, ….*"). Markers must hug non-space text so a bare
// multiplication asterisk ("3 * 4") is left alone.
const EMPHASIS_RE = /\*(\S(?:[^*]*\S)?)\*/g;

const DELIMITED_MATH_RE = /\\[([]\s*([\s\S]*?)\s*\\[)\]]/g;

// A $...$ span is unwrapped when its contents look like math: either a LaTeX
// token, or operators with no prose words. Dollar amounts in word problems
// ("$5 and $3 of apples") survive untouched.
const DOLLAR_SPAN_RE = /\$([^$\n]+)\$/g;
const LATEX_TOKEN_RE = /[\\^_]/;
const PROSE_WORD_RE = /[a-zA-Z]{2,}/;
const MATH_OPERATOR_RE = /[+\-*/=<>×÷()?]/;
const LONE_VARIABLE_RE = /^\s*[a-zA-Z]\s*$/;

const FRAC_RE = /\\[dt]?frac\{([^{}]+)\}\{([^{}]+)\}/g;

// After conversion, unicodeit leaves grouping braces behind ({π}² or √{2});
// unwrap braces around a single token. Spans with spaces or commas (set
// notation like {1, 2, 3}) are preserved.
const LONE_BRACE_GROUP_RE = /\{([^{}\s,;]+)\}/g;

// unicodeit treats every "-" as math-mode minus (−); restore the hyphen when
// it sits between letters ("unknown-factor"). Digit contexts (32 − 8) keep
// the minus sign.
const PROSE_HYPHEN_RE = /(?<=[a-zA-Z])−(?=[a-zA-Z0-9])|(?<=[0-9])−(?=[a-zA-Z])/g;

/**
 * Converts LaTeX markup in mixed text to plain Unicode for display:
 * "Multiply $\frac{2}{3} \times x^2$" → "Multiply ⅔ × x²".
 */
export function latexToUnicode(text: string): string {
  let result = text
    .replace(EMPHASIS_RE, (_match, inner: string) => inner)
    .replace(
      DELIMITED_MATH_RE,
      (match, inner: string) =>
        (match.startsWith('\\(') && match.endsWith('\\)')) ||
        (match.startsWith('\\[') && match.endsWith('\\]'))
          ? inner
          : match,
    )
    .replace(DOLLAR_SPAN_RE, (match, inner: string) => {
      const isMath =
        LATEX_TOKEN_RE.test(inner) ||
        LONE_VARIABLE_RE.test(inner) ||
        (!PROSE_WORD_RE.test(inner) && MATH_OPERATOR_RE.test(inner));
      return isMath ? inner : match;
    })
    .replace(
      FRAC_RE,
      (_match, num: string, den: string) => VULGAR_FRACTIONS[`${num}/${den}`] ?? `${num}/${den}`,
    );
  for (const [pattern, glyph] of EXTRA_SYMBOLS) {
    result = result.replace(pattern, glyph);
  }
  return replace(result)
    .replace(LONE_BRACE_GROUP_RE, (_match, inner: string) => inner)
    .replace(PROSE_HYPHEN_RE, '-');
}

/**
 * Returns a copy of a JSON-compatible value with latexToUnicode applied to
 * every string. Display-only — don't feed the result back to an evaluator.
 */
export function latexToUnicodeDeep<T>(value: T): T {
  if (typeof value === 'string') return latexToUnicode(value) as T;
  if (Array.isArray(value)) return value.map(latexToUnicodeDeep) as T;
  if (value !== null && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value).map(([key, inner]) => [key, latexToUnicodeDeep(inner)]),
    ) as T;
  }
  return value;
}
