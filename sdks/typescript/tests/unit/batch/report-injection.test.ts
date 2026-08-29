import { describe, it, expect } from 'vitest';
import { formatAsHTML } from '../../../src/batch/formatters.js';
import { injectReportData, toInlineJson } from '../../../src/batch/report-injection.js';
import type { BatchOutput, BatchResult } from '../../../src/batch/types.js';

/**
 * Evaluated text and model reasoning both reach the report payload, so anything a caller
 * can put in a CSV cell ends up inside an inline `<script>`. These guard the two ways that
 * has broken: `$`-patterns in a replacement string, and characters that terminate a script.
 *
 * Counting `</script>` rather than measuring the payload's length: the spliced template
 * tail contains newlines, so a length check on the payload line misses it entirely.
 */

const MARKER_TEMPLATE = 'head var REPORT_DATA = null; // __REPLACED_BY_FORMATTER__ tail</script>end';

function reportFor(text: string): string {
  const result: BatchResult = {
    rowIndex: 0,
    text,
    gradeLevel: '5',
    evaluatorId: 'student_facing_text.ela_reading.purpose_clarity',
    status: 'success',
    score: 'slightly_complex',
    reasoning: text,
    processingTimeMs: 1,
    columns: { text, grade_level: '5' },
    originalRow: { text, grade_level: '5' },
  };

  return formatAsHTML(
    {
      results: [result],
      summary: { totalTasks: 1, successful: 1, failed: 0, durationMs: 1, resultsPerEvaluator: {} },
    } satisfies BatchOutput,
    {
      csvPath: 'in.csv',
      groupId: 'text-complexity',
      reportId: 'r1',
      generatedAt: new Date('2026-08-29T00:00:00Z'),
      totalInputRows: 1,
    },
  );
}

const closingTags = (html: string) => (html.match(/<\/script>/g) ?? []).length;

/**
 * The injected payload, parsed back.
 *
 * Tag counting alone is not enough: `$&` and `` $` `` corrupt the JSON without adding a
 * closing tag, so a report can be structurally intact and still carry unparseable data —
 * which renders as an empty report rather than an obvious failure.
 */
function injectedPayload(html: string): unknown {
  const line = html.split('\n').find((l) => l.trimStart().startsWith('var REPORT_DATA = {'));
  if (!line) throw new Error('no injected REPORT_DATA assignment found');
  const json = line.slice(line.indexOf('{'), line.lastIndexOf('}') + 1);
  return JSON.parse(json.replace(/\\u003c/g, '<').replace(/\\u003e/g, '>').replace(/\\u0026/g, '&'));
}

describe('the text-complexity report survives hostile evaluated text', () => {
  const baseline = closingTags(reportFor('An ordinary passage.'));

  it.each([
    ["$' — inserts everything after the match", "A passage containing $' a quote."],
    ['$` — inserts everything before it', 'A passage containing $` a quote.'],
    ['$& — inserts the match itself', 'A passage containing $& a quote.'],
    ['$$ — an escaped dollar', 'A passage costing $$5.'],
  ])('%s does not splice the template', (_name, text) => {
    // A string replacement treats these as substitution patterns; `$'` alone took this
    // report from one closing tag to three, and the others corrupt the JSON silently.
    const html = reportFor(text);

    expect(closingTags(html)).toBe(baseline);
    const payload = injectedPayload(html) as { items?: unknown[] };
    expect(payload).toBeTypeOf('object');
    // The text survives intact rather than being partly replaced by template fragments.
    // injectedPayload already reverses the unicode escaping, so compare verbatim.
    expect(JSON.stringify(payload)).toContain(text);
  });

  it('escapes markup so evaluated text cannot close the script element', () => {
    const html = reportFor('</script><img src=x onerror=alert(1)>');

    expect(closingTags(html)).toBe(baseline);
    expect(html).toContain('\\u003c');
  });

  it('keeps the payload parseable when text carries a line separator', () => {
    // U+2028 is valid JSON but a line terminator to a pre-ES2019 parser.
    const html = reportFor('A passage with \u2028 inside.');

    expect(html).toContain('\\u2028');
    expect(html).not.toContain('\u2028');
  });
});

describe('injectReportData', () => {
  it('treats the payload as literal text, not a replacement pattern', () => {
    const out = injectReportData(MARKER_TEMPLATE, `{"t":"$'"}`, 'Test');

    // With a string replacement, `$'` would have inserted ` tail</script>end` here.
    expect(out).toBe(`head var REPORT_DATA = {"t":"$'"}; tail</script>end`);
  });

  it('names the report when the template has lost its marker', () => {
    expect(() => injectReportData('<html>no marker</html>', '{}', 'Standards')).toThrow(
      /Standards report template injection marker not found/,
    );
  });
});

describe('toInlineJson', () => {
  it('escapes the characters that can end a script element', () => {
    const out = toInlineJson({ a: '<b>&</b>' });

    expect(out).not.toMatch(/[<>&]/);
    expect(out).toContain('\\u003c');
    expect(out).toContain('\\u0026');
  });

  it('leaves a dollar pattern untouched — the caller must not re-expand it', () => {
    expect(toInlineJson({ a: "$'" })).toContain("$'");
  });
});
