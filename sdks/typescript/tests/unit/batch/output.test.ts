import { describe, it, expect } from 'vitest';
import { renderOutputs } from '../../../src/batch/output.js';
import { injectReportData } from '../../../src/batch/report-injection.js';
import type { BatchOutput, BatchResult, ReportMeta } from '../../../src/batch/index.js';

const meta: ReportMeta = {
  csvPath: '/tmp/corpus.csv',
  groupId: 'math-standards-alignment',
  reportId: 'corpus_2026',
  generatedAt: new Date('2026-08-08T00:00:00Z'),
  totalInputRows: 2,
};

function standardsResult(over: Partial<BatchResult> = {}): BatchResult {
  return {
    rowIndex: 2,
    text: '2+2=?',
    gradeLevel: '4',
    evaluatorId: 'academic_standards_alignment.mathematics.math_standards_alignment',
    status: 'success',
    score: '1/2',
    reasoning: '1 of 2 learning components aligned',
    processingTimeMs: 10,
    originalRow: { id: 'itm-1', ccss_standard: '4.OA.A.1', question: '2+2=?' },
    payload: {
      statementCode: '4.OA.A.1',
      question: '2+2=?',
      jurisdiction: 'Multi-State',
      alignedCount: 1,
      totalCount: 2,
      learningComponents: [
        { identifier: 'lc1', description: 'Add within 100', aligned: true, reasoning: 'r1', feedback: '' },
        { identifier: 'lc2', description: 'Multiply', aligned: false, reasoning: 'r2', feedback: 'make it multiply' },
      ],
    },
    ...over,
  };
}

function output(results: BatchResult[]): BatchOutput {
  return {
    results,
    summary: {
      totalTasks: results.length,
      successful: results.filter((r) => r.status === 'success').length,
      failed: results.filter((r) => r.status === 'error').length,
      durationMs: 100,
      resultsPerEvaluator: {},
    },
  };
}

describe('renderOutputs — standards family', () => {
  it('JSON carries per-component detail and the original row for joining', () => {
    const bundle = renderOutputs('math-standards-alignment', output([standardsResult()]), meta);
    const parsed = JSON.parse(bundle.json);
    expect(parsed.meta.family).toBe('math-standards-alignment');
    expect(parsed.items).toHaveLength(1);
    const item = parsed.items[0];
    expect(item.id).toBe('itm-1');
    expect(item.alignedCount).toBe(1);
    expect(item.totalCount).toBe(2);
    expect(item.learningComponents).toHaveLength(2);
    expect(item.originalRow.ccss_standard).toBe('4.OA.A.1'); // joinable back to source
  });

  it('CSV flattens roll-ups, computes ratio, and preserves original columns', () => {
    const bundle = renderOutputs('math-standards-alignment', output([standardsResult()]), meta);
    const [header, row] = bundle.csv.split('\n');
    expect(header).toContain('aligned_count');
    expect(header).toContain('aligned_ratio');
    expect(header).toContain('id'); // passthrough original column
    expect(row).toContain('0.500'); // 1/2
    expect(row).toContain('4.OA.A.1');
  });

  it('prefixes verdict columns that collide with source columns (joinable, no dupes)', () => {
    const r = standardsResult({ originalRow: { id: 'x', jurisdiction: 'California', statement_code: '4.OA.A.1' } });
    const [header] = renderOutputs('math-standards-alignment', output([r]), meta).csv.split('\n');
    const cols = header.split(',');
    // Source columns kept as-is; colliding verdict columns are namespaced.
    expect(cols.filter((c) => c === 'jurisdiction')).toHaveLength(1);
    expect(cols).toContain('verdict_jurisdiction');
    expect(cols).toContain('verdict_statement_code');
    // Non-colliding verdict columns keep clean names.
    expect(cols).toContain('aligned_ratio');
  });

  it('HTML injects report data and leaves no placeholder marker', () => {
    const bundle = renderOutputs('math-standards-alignment', output([standardsResult()]), meta);
    expect(bundle.html).not.toContain('__REPLACED_BY_FORMATTER__');
    expect(bundle.html).toContain('var REPORT_DATA = {');
    expect(bundle.html).toContain('4.OA.A.1');
  });

  it('surfaces an errored row without a payload, keeping source context', () => {
    const errored = standardsResult({
      status: 'error', error: 'Standard not found', payload: undefined, score: undefined,
      originalRow: { id: 'e1', ccss_standard: '4.OA.A.1', jurisdiction: 'Texas' },
    });
    const parsed = JSON.parse(renderOutputs('math-standards-alignment', output([errored]), meta).json);
    expect(parsed.items[0].status).toBe('error');
    expect(parsed.items[0].error).toBe('Standard not found');
    expect(parsed.items[0].alignedCount).toBeNull();
    // Error rows still carry jurisdiction/statementCode from the source row.
    expect(parsed.items[0].jurisdiction).toBe('Texas');
    expect(parsed.items[0].statementCode).toBe('4.OA.A.1');
  });

  it('CSV header is the union of source columns across all rows', () => {
    const r1 = standardsResult({ originalRow: { id: 'a', ccss_standard: 'x' } });
    const r2 = standardsResult({ rowIndex: 3, originalRow: { id: 'b', extra: 'y' } });
    const [header] = renderOutputs('math-standards-alignment', output([r1, r2]), meta).csv.split('\n');
    const cols = header.split(',');
    expect(cols).toContain('extra'); // present only in the second row
    expect(cols).toContain('ccss_standard'); // present only in the first row
  });
});

describe('renderOutputs — text-complexity family (generic JSON)', () => {
  it('emits one result per (row, evaluator) with score/reasoning', () => {
    const qtcResult: BatchResult = {
      rowIndex: 2, text: 'hello', gradeLevel: '3', evaluatorId: 'vocabulary', status: 'success',
      score: 'slightly complex', reasoning: 'simple words', processingTimeMs: 5,
      originalRow: { text: 'hello', grade_level: '3' },
    };
    const bundle = renderOutputs('text-complexity', output([qtcResult]), { ...meta, groupId: 'text-complexity' });
    const parsed = JSON.parse(bundle.json);
    expect(parsed.results[0].evaluatorId).toBe('vocabulary');
    expect(parsed.results[0].score).toBe('slightly complex');
  });

  it('orders results by row, then by evaluator id within a row', () => {
    const qtc = (rowIndex: number, evaluatorId: string): BatchResult => ({
      rowIndex, text: 't', gradeLevel: '3', evaluatorId, status: 'success',
      score: 'slightly complex', reasoning: '', processingTimeMs: 1,
      originalRow: { text: 't', grade_level: '3' },
    });
    // Deliberately unsorted, with a same-row pair so the tiebreak is exercised.
    const bundle = renderOutputs(
      'text-complexity',
      output([qtc(3, 'vocabulary'), qtc(2, 'vocabulary'), qtc(2, 'conventionality')]),
      { ...meta, groupId: 'text-complexity' },
    );

    const parsed = JSON.parse(bundle.json);
    expect(parsed.results.map((r: { rowIndex: number; evaluatorId: string }) => `${r.rowIndex}:${r.evaluatorId}`))
      .toEqual(['2:conventionality', '2:vocabulary', '3:vocabulary']);
  });
});

describe('renderOutputs — empty result sets', () => {
  it('produces an empty standards CSV rather than a bare header', () => {
    const bundle = renderOutputs('math-standards-alignment', output([]), meta);
    expect(bundle.csv).toBe('');
  });

  it('still produces parseable JSON and HTML when nothing ran', () => {
    const bundle = renderOutputs('math-standards-alignment', output([]), meta);
    expect(() => JSON.parse(bundle.json)).not.toThrow();
    expect(bundle.html).not.toContain('__REPLACED_BY_FORMATTER__');
  });
});

describe('injectReportData', () => {
  it('replaces the marker with the payload assignment', () => {
    const out = injectReportData(
      'before var REPORT_DATA = null; // __REPLACED_BY_FORMATTER__ after',
      '{"a":1}',
      'Standards',
    );
    expect(out).toContain('var REPORT_DATA = {"a":1};');
    expect(out).not.toContain('__REPLACED_BY_FORMATTER__');
  });

  it('throws rather than emitting a report with no data when the marker is missing', () => {
    expect(() => injectReportData('<html>no marker here</html>', '{}', 'Standards')).toThrow(/marker not found/);
  });

  // As a replacement *string*, `$$`/`$&`/`$'` are substitution patterns: `$$x^2$$`
  // would collapse to `$x^2$` and `$'` would splice the template tail — including
  // the closing </script> — into the inline script.
  it.each([
    ['$$ (LaTeX)', '{"q":"Evaluate $$x^2$$"}'],
    ["$' (tail splice)", `{"q":"see $' here"}`],
    ['$& (whole match)', '{"q":"a $& b"}'],
    ['$` (prefix)', '{"q":"a $` b"}'],
  ])('inserts %s verbatim instead of expanding it', (_label, payload) => {
    const template = `<script>\nvar REPORT_DATA = null; // __REPLACED_BY_FORMATTER__\n</script>\n<div>TAIL</div>`;
    const out = injectReportData(template, payload, 'Standards');

    expect(out).toContain(`var REPORT_DATA = ${payload};`);
    // Exactly one closing script tag: the tail was not spliced into the script.
    expect(out.match(/<\/script>/g)).toHaveLength(1);
  });
});

describe('standards CSV — escaping, header contract, and blank handling', () => {
  it('emits the exact header row so downstream joins have a stable contract', () => {
    const bundle = renderOutputs('math-standards-alignment', output([standardsResult()]), meta);
    expect(bundle.csv.split('\n')[0]).toBe(
      'id,ccss_standard,question,statement_code,jurisdiction,aligned_count,total_count,aligned_ratio,status,error,learning_components_json',
    );
  });

  it('quotes and doubles-up fields containing a comma, quote or newline', () => {
    const nasty = 'He said "hi", then\nleft';
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({ originalRow: { id: 'itm-1', ccss_standard: '4.OA.A.1', question: nasty } })]),
      meta,
    );
    // The whole field is quoted and its inner quotes doubled, so the row still parses.
    expect(bundle.csv).toContain('"He said ""hi"", then\nleft"');
  });

  it('leaves the ratio blank rather than dividing by zero', () => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({ payload: { statementCode: '4.OA.A.1', question: 'q', jurisdiction: 'Multi-State', alignedCount: 0, totalCount: 0, learningComponents: [] } })]),
      meta,
    );
    const row = bundle.csv.split('\n')[1].split(',');
    // aligned_count, total_count, aligned_ratio, status, error, learning_components_json
    expect(row.slice(-6)).toEqual(['0', '0', '', 'success', '', '[]']);
  });

  it('writes an empty error cell on success and the message on failure', () => {
    const ok = renderOutputs('math-standards-alignment', output([standardsResult()]), meta);
    expect(JSON.parse(ok.json).items[0].error).toBeNull();

    const bad = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({ status: 'error', error: 'KG timeout', score: undefined, payload: undefined })]),
      meta,
    );
    expect(bad.csv).toContain('KG timeout');
    expect(JSON.parse(bad.json).items[0].error).toBe('KG timeout');

    // Counts blank rather than "null", and no components, so the row still parses.
    const cells = bad.csv.split('\n')[1].split(',');
    expect(cells.slice(-6)).toEqual(['', '', '', 'error', 'KG timeout', '[]']);
    expect(JSON.parse(bad.json).items[0].learningComponents).toEqual([]);
  });

  // normalizeRow matches headers case-insensitively and via the family's aliases,
  // so anything accepted on input must survive into the outputs.
  it.each([
    ['canonical, normalized', { columns: { id: 'itm-9', statementCode: '5.NF.B.3', jurisdiction: 'Utah' } }],
    ['aliased + capitalized source headers', {
      columns: undefined,
      originalRow: { Item_ID: 'itm-9', CCSS_Standard: '5.NF.B.3', Jurisdiction: 'Utah' },
    }],
    // Blank/null/padded keys must all fall through to a populated alias rather
    // than resolving to '' or the string "null".
    ['blank, null and padded keys, falling through to a populated alias', {
      columns: { id: '', statementCode: '', jurisdiction: '' },
      originalRow: {
        statementCode: '',
        statement_code: null,
        Item_ID: 'itm-9',
        CCSS_Standard: '5.NF.B.3',
        '  Jurisdiction  ': 'Utah',
      },
    }],
  ])('carries id/statementCode/jurisdiction from %s onto an error row', (_label, over) => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({ status: 'error', error: 'KG 401', score: undefined, payload: undefined, ...over })]),
      meta,
    );
    const [item] = JSON.parse(bundle.json).items;
    expect(item.id).toBe('itm-9');
    expect(item.statementCode).toBe('5.NF.B.3');
    expect(item.jurisdiction).toBe('Utah');
  });

  it('orders rows by source row index regardless of completion order', () => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([
        standardsResult({ rowIndex: 4, originalRow: { id: 'c' } }),
        standardsResult({ rowIndex: 2, originalRow: { id: 'a' } }),
        standardsResult({ rowIndex: 3, originalRow: { id: 'b' } }),
      ]),
      meta,
    );
    expect(JSON.parse(bundle.json).items.map((i: { id: string }) => i.id)).toEqual(['a', 'b', 'c']);
  });

  it('falls back to the result text for question, and blanks a missing grade', () => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({
        status: 'error', error: 'boom', payload: undefined, gradeLevel: undefined,
        text: 'question from the row', originalRow: { id: 'itm-9' },
      })]),
      meta,
    );
    const row = JSON.parse(bundle.json).items[0];
    expect(row.question).toBe('question from the row');
    expect(row.gradeLevel).toBe('');
  });

  it('lists a column shared by several rows only once', () => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([
        standardsResult({ rowIndex: 2, originalRow: { id: 'a', question: 'q1' } }),
        standardsResult({ rowIndex: 3, originalRow: { id: 'b', question: 'q2' } }),
      ]),
      meta,
    );
    const header = bundle.csv.split('\n')[0].split(',');
    expect(header.filter((h) => h === 'id')).toHaveLength(1);
    expect(header.filter((h) => h === 'question')).toHaveLength(1);
  });

  it('blanks a column absent from a ragged row rather than writing undefined', () => {
    const bundle = renderOutputs(
      'math-standards-alignment',
      output([
        standardsResult({ rowIndex: 2, originalRow: { id: 'a', extra: 'present' } }),
        standardsResult({ rowIndex: 3, originalRow: { id: 'b' } }),
      ]),
      meta,
    );
    const lines = bundle.csv.split('\n');
    expect(lines[0].split(',').slice(0, 2)).toEqual(['id', 'extra']);
    expect(lines[2].startsWith('b,,')).toBe(true);
  });
});

describe('standards HTML — payload escaping', () => {
  function htmlFor(question: string): string {
    const { html } = renderOutputs(
      'math-standards-alignment',
      output([standardsResult({ payload: { statementCode: '4.OA.A.1', question, jurisdiction: 'Multi-State', alignedCount: 1, totalCount: 2, learningComponents: [] } })]),
      meta,
    );
    // The standards family has a report of its own; a bundle without one here would mean
    // the dispatch stopped finding it, which the assertions below could not distinguish.
    if (!html) throw new Error('standards family emitted no HTML report');
    return html;
  }

  it('escapes angle brackets and ampersands so the payload cannot close the script tag', () => {
    const html = htmlFor('</script><img src=x onerror=alert(1)>&');
    expect(html).not.toContain('</script><img');
    expect(html).toContain('\\u003c');
    expect(html).toContain('\\u003e');
    expect(html).toContain('\\u0026');
  });

  it('escapes U+2028 and U+2029, which are valid JSON but break inline script parsing', () => {
    const html = htmlFor('line\u2028break\u2029here');
    expect(html).toContain('\\u2028');
    expect(html).toContain('\\u2029');
    expect(html).not.toMatch(/[\u2028\u2029]/);
  });
});
