import { describe, it, expect } from 'vitest';
import { renderOutputs } from '../../../src/batch/output.js';
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
    grade: '4',
    evaluatorId: 'math.standards-alignment',
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

  it('surfaces an errored row without a payload', () => {
    const errored = standardsResult({ status: 'error', error: 'Standard not found', payload: undefined, score: undefined });
    const parsed = JSON.parse(renderOutputs('math-standards-alignment', output([errored]), meta).json);
    expect(parsed.items[0].status).toBe('error');
    expect(parsed.items[0].error).toBe('Standard not found');
    expect(parsed.items[0].alignedCount).toBeNull();
  });
});

describe('renderOutputs — text-complexity family (generic JSON)', () => {
  it('emits one result per (row, evaluator) with score/reasoning', () => {
    const qtcResult: BatchResult = {
      rowIndex: 2, text: 'hello', grade: '3', evaluatorId: 'vocabulary', status: 'success',
      score: 'slightly complex', reasoning: 'simple words', processingTimeMs: 5,
      originalRow: { text: 'hello', grade: '3' },
    };
    const bundle = renderOutputs('text-complexity', output([qtcResult]), { ...meta, groupId: 'text-complexity' });
    const parsed = JSON.parse(bundle.json);
    expect(parsed.results[0].evaluatorId).toBe('vocabulary');
    expect(parsed.results[0].score).toBe('slightly complex');
  });
});
