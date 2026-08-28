import { describe, it, expect } from 'vitest';
import {
  formatAsCSV,
  formatAsHTML,
  type ReportMeta,
  type BatchOutput,
  type BatchResult,
} from '../../../src/batch/index.js';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/index.js';

// The report singles GLA out to derive on-band/off-target status, so this id has to
// match the evaluator. Other evaluator ids in this file are arbitrary grouping labels.
const GLA_ID = GradeLevelAppropriatenessEvaluator.metadata.id;

// ---- Test fixtures ----

function makeResult(overrides: Partial<BatchResult>): BatchResult {
  return {
    rowIndex: 1,
    text: 'Sample text.',
    gradeLevel: '5',
    evaluatorId: 'vocabulary',
    status: 'success',
    score: 'slightly complex',
    reasoning: 'ok',
    processingTimeMs: 100,
    originalRow: { text: 'Sample text.', grade_level: '5' },
    ...overrides,
  };
}

function makeOutput(results: BatchResult[]): BatchOutput {
  return {
    results,
    summary: {
      totalTasks: results.length,
      successful: results.filter(r => r.status === 'success').length,
      failed: results.filter(r => r.status === 'error').length,
      durationMs: 1000,
      resultsPerEvaluator: {},
    },
  };
}

function makeMeta(overrides?: Partial<ReportMeta>): ReportMeta {
  return {
    csvPath: '/data/input.csv',
    groupId: 'text-complexity',
    reportId: 'test_20260301T0000',
    generatedAt: new Date('2026-03-01T00:00:00Z'),
    totalInputRows: 1,
    ...overrides,
  };
}

/**
 * Extracts and parses the REPORT_DATA JSON injected into the HTML by formatAsHTML.
 * This lets us make assertions on actual computed values rather than raw string presence.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function extractReportData(html: string): any {
  const marker = 'var REPORT_DATA = ';
  const start = html.indexOf(marker) + marker.length;
  const line = html.slice(start, html.indexOf('\n', start));
  const json = line.endsWith(';') ? line.slice(0, -1) : line;
  return JSON.parse(json);
}

// ============================================================
// Evaluator id -> column and label derivation
// ============================================================

describe('deriving columns and labels from a registry id', () => {
  // Registry ids are dotted and snake_case. Everything user-visible in the report is
  // derived from the last segment, so a dotted id must not leak its namespace into a
  // CSV header, an HTML row field, or a display label.
  const DOTTED = 'student_facing_text.ela_reading.vocabulary_complexity';

  it('uses only the last id segment for CSV column names', () => {
    const csv = formatAsCSV(makeOutput([makeResult({ evaluatorId: DOTTED })]));
    const header = csv.split('\n')[0];

    expect(header).toContain('vocabulary_complexity_score');
    expect(header).toContain('vocabulary_complexity_reasoning');
    expect(header).toContain('vocabulary_complexity_status');
    expect(header).not.toContain('student_facing_text');
  });

  it('uses only the last id segment for HTML row fields, one column per evaluator', () => {
    const other = 'student_facing_text.ela_reading.meaning_directness';
    const html = formatAsHTML(
      makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: DOTTED, score: 'very complex' }),
        makeResult({ rowIndex: 1, evaluatorId: other, score: 'slightly complex' }),
      ]),
      makeMeta(),
    );
    const row = extractReportData(html).fullResults.rows[0];

    // Each evaluator's score lands under its own prefix, so neither can read as the other's.
    expect(row['__vocabulary_complexity_score']).toBe('very complex');
    expect(row['__meaning_directness_score']).toBe('slightly complex');
    expect(Object.keys(row).some(k => k.includes('student_facing_text'))).toBe(false);
  });

  it('renders a display name from the last id segment', () => {
    const html = formatAsHTML(makeOutput([makeResult({ evaluatorId: DOTTED })]), makeMeta());
    const { complexityEvaluators } = extractReportData(html).fullResults;

    expect(complexityEvaluators).toEqual([
      { evaluatorId: DOTTED, name: 'Vocabulary Complexity', prefix: 'vocabulary_complexity' },
    ]);
  });

  it('still handles a hyphenated id with no namespace', () => {
    const csv = formatAsCSV(makeOutput([makeResult({ evaluatorId: 'sentence-structure' })]));

    expect(csv.split('\n')[0]).toContain('sentence_structure_score');
  });
});

// ============================================================
// formatAsCSV
// ============================================================

describe('formatAsCSV', () => {
  it('returns empty string for empty results', () => {
    expect(formatAsCSV(makeOutput([]))).toBe('');
  });

  it('produces one data row per input row, not per evaluator task', () => {
    // Row 1 has two evaluators → should collapse into a single CSV row
    const output = makeOutput([
      makeResult({ rowIndex: 1, evaluatorId: 'vocabulary',         score: 'slightly complex' }),
      makeResult({ rowIndex: 1, evaluatorId: 'sentence-structure', score: 'Moderately Complex' }),
    ]);

    const lines = formatAsCSV(output).split('\n');
    expect(lines).toHaveLength(2); // 1 header + 1 data row
  });

  it('places evaluator columns in alphabetical order after original columns', () => {
    const output = makeOutput([
      makeResult({ evaluatorId: 'vocabulary',         originalRow: { id: '1', text: 'txt', grade_level: '5' } }),
      makeResult({ evaluatorId: 'sentence-structure', originalRow: { id: '1', text: 'txt', grade_level: '5' } }),
    ]);

    const header = formatAsCSV(output).split('\n')[0];
    const cols = header.split(',');

    // Original columns come first
    expect(cols[0]).toBe('id');
    // sentence-structure sorts before vocabulary alphabetically
    expect(cols.indexOf('sentence_structure_score')).toBeLessThan(cols.indexOf('vocabulary_score'));
  });

  it('leaves score empty and puts error message in reasoning for failed evaluations', () => {
    const output = makeOutput([
      makeResult({ status: 'error', error: 'API timeout', score: undefined }),
    ]);

    const csv = formatAsCSV(output);
    const dataRow = csv.split('\n')[1];
    const cols = dataRow.split(',');
    const header = csv.split('\n')[0].split(',');

    const scoreIdx = header.indexOf('vocabulary_score');
    const reasoningIdx = header.indexOf('vocabulary_reasoning');
    const statusIdx = header.indexOf('vocabulary_status');

    expect(cols[scoreIdx]).toBe('');           // score is blank for errors
    expect(cols[reasoningIdx]).toBe('API timeout');
    expect(cols[statusIdx]).toBe('error');
  });

  it('outputs not_run when an evaluator produced no result for a row', () => {
    // Row 1: vocabulary ran; sentence-structure did not
    const output = makeOutput([
      makeResult({ rowIndex: 1, evaluatorId: 'vocabulary', originalRow: { text: 'x', grade_level: '5' } }),
    ]);
    // Manually add sentence-structure to the results so the column exists but not for row 1
    output.results.push(makeResult({
      rowIndex: 2, evaluatorId: 'sentence-structure',
      originalRow: { text: 'y', grade_level: '5' },
    }));

    const csv = formatAsCSV(output);
    const [header, row1] = csv.split('\n');
    const cols = header.split(',');
    const ssStatusIdx = cols.indexOf('sentence_structure_status');

    expect(row1.split(',')[ssStatusIdx]).toBe('not_run');
  });

  it('wraps fields containing commas, quotes, or newlines in double-quotes', () => {
    const output = makeOutput([
      makeResult({
        score: 'slightly complex',
        reasoning: 'Has "quotes" and, comma',
        originalRow: { text: 'Line1\nLine2', grade_level: '5' },
      }),
    ]);

    const csv = formatAsCSV(output);
    expect(csv).toContain('"Line1\nLine2"');
    expect(csv).toContain('"Has ""quotes"" and, comma"');
  });
});

// ============================================================
// formatAsHTML — computed report data
// ============================================================

describe('formatAsHTML', () => {
  describe('snapshot counts', () => {
    it('counts a row as errored if any of its evaluator results failed', () => {
      // Row 1: vocabulary ok, sentence-structure errored → should be "errored"
      // Row 2: both ok → should be "processed"
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary',         status: 'success' }),
        makeResult({ rowIndex: 1, evaluatorId: 'sentence-structure', status: 'error', error: 'timeout' }),
        makeResult({ rowIndex: 2, evaluatorId: 'vocabulary',         status: 'success' }),
        makeResult({ rowIndex: 2, evaluatorId: 'sentence-structure', status: 'success' }),
      ]);

      const { meta } = extractReportData(formatAsHTML(output, makeMeta({ totalInputRows: 2 })));
      expect(meta.processedRows).toBe(1);
      expect(meta.erroredRows).toBe(1);
    });
  });

  describe('GLA status classification', () => {
    function glaOutput(inputGrade: string, glaBand: string) {
      return makeOutput([makeResult({
        gradeLevel: inputGrade,
        evaluatorId: GLA_ID,
        score: glaBand,
      })]);
    }

    it('classifies on-band when input grade falls within the GLA band', () => {
      const { gradeLevelStats } = extractReportData(
        formatAsHTML(glaOutput('3', '2-3'), makeMeta())
      );
      expect(gradeLevelStats.onBand).toBe(1);
      expect(gradeLevelStats.adjacent).toBe(0);
      expect(gradeLevelStats.offTarget).toBe(0);
    });

    it('classifies adjacent when input grade is one band away from the GLA result', () => {
      // Grade 4 → band index 2 (4-5); GLA "2-3" → band index 1; diff = 1
      const { gradeLevelStats } = extractReportData(
        formatAsHTML(glaOutput('4', '2-3'), makeMeta())
      );
      expect(gradeLevelStats.onBand).toBe(0);
      expect(gradeLevelStats.adjacent).toBe(1);
      expect(gradeLevelStats.offTarget).toBe(0);
    });

    it('classifies off-target when input grade is two or more bands away', () => {
      // Grade 8 → band index 3 (6-8); GLA "2-3" → band index 1; diff = 2
      const { gradeLevelStats } = extractReportData(
        formatAsHTML(glaOutput('8', '2-3'), makeMeta())
      );
      expect(gradeLevelStats.onBand).toBe(0);
      expect(gradeLevelStats.adjacent).toBe(0);
      expect(gradeLevelStats.offTarget).toBe(1);
    });

    it('maps grade K and grade 1 to the same K-1 band (both on-band with K-1 GLA result)', () => {
      for (const grade of ['K', '1']) {
        const { gradeLevelStats } = extractReportData(
          formatAsHTML(glaOutput(grade, 'K-1'), makeMeta())
        );
        expect(gradeLevelStats.onBand).toBe(1);
      }
    });

    it('maps grade 11, 12, and CCR to the same 11-CCR band', () => {
      for (const grade of ['11', '12', 'CCR']) {
        const { gradeLevelStats } = extractReportData(
          formatAsHTML(glaOutput(grade, '11-CCR'), makeMeta())
        );
        expect(gradeLevelStats.onBand).toBe(1);
      }
    });

    it('treats an unrecognised grade as off-target (tests the -1 guard, not coincidental diff arithmetic)', () => {
      // Grade '99' → gradeToBandIndex returns -1. GLA 'K-1' is index 0, so without
      // the "inputIdx === -1" guard the diff would be |(-1) - 0| = 1 → 'adjacent'.
      // The guard must fire for this to be 'off-target'.
      const { gradeLevelStats } = extractReportData(
        formatAsHTML(glaOutput('99', 'K-1'), makeMeta())
      );
      expect(gradeLevelStats.offTarget).toBe(1);
    });
  });

  describe('complexity stats', () => {
    it('normalises score strings case-insensitively (Title Case and lowercase both map to the same numeric value)', () => {
      // vocabulary returns lowercase; sentence-structure returns Title Case
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary',         score: 'slightly complex' }),
        makeResult({ rowIndex: 1, evaluatorId: 'sentence-structure', score: 'Slightly Complex' }),
      ]);

      const { complexityStats } = extractReportData(
        formatAsHTML(output, makeMeta())
      );

      // Both evaluators must appear — verifies GLA is excluded and neither evaluator was silently dropped
      expect(complexityStats).toHaveLength(2);
      for (const stat of complexityStats) {
        expect(stat.average).toBe(1.0);
        expect(stat.label).toBe('Slightly Complex');
        expect(stat.distribution[0]).toBe(1); // one score of 1
      }
    });

    it('excludes GLA from complexity stats even when it runs alongside complexity evaluators', () => {
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: GLA_ID, score: '4-5' }),
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary', score: 'slightly complex' }),
      ]);

      const { complexityStats } = extractReportData(
        formatAsHTML(output, makeMeta())
      );

      expect(complexityStats).toHaveLength(1);
      expect(complexityStats[0].evaluatorId).toBe('vocabulary');
    });

    it('computes average and distribution correctly across multiple rows', () => {
      // scores: 1, 2, 3 → avg 2.0
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary', score: 'slightly complex' }),
        makeResult({ rowIndex: 2, evaluatorId: 'vocabulary', score: 'moderately complex' }),
        makeResult({ rowIndex: 3, evaluatorId: 'vocabulary', score: 'very complex' }),
      ]);

      const { complexityStats } = extractReportData(formatAsHTML(output, makeMeta({ totalInputRows: 3 })));
      const vocab = complexityStats[0];

      expect(vocab.average).toBe(2.0);
      expect(vocab.label).toBe('Moderately Complex');
      expect(vocab.distribution).toEqual([1, 1, 1, 0]); // one each of scores 1, 2, 3
    });

    it('labels average >= 3.5 as Exceedingly Complex', () => {
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary', score: 'exceedingly complex' }),
        makeResult({ rowIndex: 2, evaluatorId: 'vocabulary', score: 'exceedingly complex' }),
      ]);

      const { complexityStats } = extractReportData(formatAsHTML(output, makeMeta({ totalInputRows: 2 })));
      expect(complexityStats[0].label).toBe('Exceedingly Complex');
      expect(complexityStats[0].distribution).toEqual([0, 0, 0, 2]);
    });

    it('excludes error results from complexity averages', () => {
      const output = makeOutput([
        makeResult({ rowIndex: 1, evaluatorId: 'vocabulary', status: 'success', score: 'very complex' }),
        makeResult({ rowIndex: 2, evaluatorId: 'vocabulary', status: 'error', error: 'timeout' }),
      ]);

      const { complexityStats } = extractReportData(formatAsHTML(output, makeMeta({ totalInputRows: 2 })));
      expect(complexityStats[0].average).toBe(3.0); // only the successful score counts
      expect(complexityStats[0].distribution).toEqual([0, 0, 1, 0]);
    });
  });

  describe('grade band distribution', () => {
    it('groups by the INPUT grade band, not the GLA result band', () => {
      // Grade 3 → "2-3" bucket (index 1). GLA says "9-10" (off-target, diff=3).
      const output = makeOutput([makeResult({
        gradeLevel: '3',
        evaluatorId: GLA_ID,
        score: '9-10',
      })]);

      const { gradeBandDistribution } = extractReportData(
        formatAsHTML(output, makeMeta())
      );

      const band23 = gradeBandDistribution.data[1]; // index 1 = "2-3" (input grade)
      const band910 = gradeBandDistribution.data[4]; // index 4 = "9-10" (GLA result)

      expect(band23.total).toBe(1);    // row belongs to the "2-3" input bucket
      expect(band23.offTarget).toBe(1);
      expect(band910.total).toBe(0);   // NOT in the GLA result's bucket
    });
  });

  describe('complexity heatmap', () => {
    it('produces null for grade bands that have no data', () => {
      // Only grade 5 rows → only "4-5" band (index 2) has data; others are null
      const output = makeOutput([
        makeResult({ gradeLevel: '5', evaluatorId: 'vocabulary', score: 'moderately complex' }),
      ]);

      const { complexityHeatmap } = extractReportData(formatAsHTML(output, makeMeta()));
      const k1Values = complexityHeatmap.values[0]; // K-1 band
      expect(k1Values[0]).toBeNull();
    });

    it('computes the correct per-cell average', () => {
      // Two grade-5 rows: scores 1 and 3 → average 2.0
      const output = makeOutput([
        makeResult({ rowIndex: 1, gradeLevel: '5', evaluatorId: 'vocabulary', score: 'slightly complex' }),
        makeResult({ rowIndex: 2, gradeLevel: '5', evaluatorId: 'vocabulary', score: 'very complex' }),
      ]);

      const { complexityHeatmap } = extractReportData(formatAsHTML(output, makeMeta({ totalInputRows: 2 })));
      const band45Values = complexityHeatmap.values[2]; // "4-5" is index 2
      expect(band45Values[0]).toBe(2.0);
    });
  });

  describe('XSS safety', () => {
    it('Unicode-escapes < > & so injected data cannot break out of the script tag', () => {
      const output = makeOutput([makeResult({
        text: '<script>alert("xss")</script>',
        originalRow: { text: '<script>alert("xss")</script>', grade_level: '5' },
      })]);

      const html = formatAsHTML(output, makeMeta());
      expect(html).not.toContain('<script>alert');
      expect(html).toContain('\\u003cscript\\u003e');
    });
  });
});
