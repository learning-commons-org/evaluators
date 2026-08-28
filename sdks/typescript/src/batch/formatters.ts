import type { BatchOutput, BatchResult } from './types.js';
import reportTemplate from './report-template.html';
import { GradeLevelAppropriatenessEvaluator } from '../evaluators/grade-level-appropriateness.js';

// ---- Constants ----

// Read from the evaluator rather than restated: the report singles GLA out to
// derive on-band/off-target status, and a stale copy here would silently drop the
// column instead of failing.
const GLA_EVALUATOR_ID = GradeLevelAppropriatenessEvaluator.metadata.id;

const GRADE_BANDS = ['K-1', '2-3', '4-5', '6-8', '9-10', '11-CCR'] as const;
type GradeBand = typeof GRADE_BANDS[number];

// Complexity string scores → numeric
const COMPLEXITY_SCORE_MAP: Record<string, number> = {
  'slightly complex': 1,
  'moderately complex': 2,
  'very complex': 3,
  'exceedingly complex': 4,
  // 'more context needed' has no numeric equivalent — rows with this score appear as N/A
  // in individual results and are excluded from aggregate stats, same as failed evaluations.
};

// ---- Helpers ----

function evaluatorDisplayName(id: string): string {
  const slug = id.split('.').pop()!;
  return slug.split(/[-_]/).map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
}

/** Maps a raw grade string (K, 1, 2 … 12, CCR) to a GRADE_BANDS index (0–5). */
function gradeToBandIndex(grade: string): number {
  const g = String(grade).trim().toUpperCase().replace(/^0+/, '');
  if (g === 'K' || g === 'KINDERGARTEN') return 0;
  if (g === '1') return 0;
  if (g === '2' || g === '3') return 1;
  if (g === '4' || g === '5') return 2;
  if (g === '6' || g === '7' || g === '8') return 3;
  if (g === '9' || g === '10') return 4;
  if (g === '11' || g === '12' || g === 'CCR') return 5;
  return -1;
}

/** Maps a GLA score string (e.g. "4-5") to a GRADE_BANDS index. */
function glaBandToIndex(band: string): number {
  return GRADE_BANDS.indexOf(band as GradeBand);
}

function getGLAStatus(inputGrade: string, glaBand: string): 'on-band' | 'adjacent' | 'off-target' {
  const inputIdx = gradeToBandIndex(inputGrade);
  const glaIdx = glaBandToIndex(glaBand);
  if (inputIdx === -1 || glaIdx === -1) return 'off-target';
  const diff = Math.abs(inputIdx - glaIdx);
  if (diff === 0) return 'on-band';
  if (diff === 1) return 'adjacent';
  return 'off-target';
}

function complexityToNumeric(score: string): number | undefined {
  // Underscores are folded so the contract's `slightly_complex` and the spaced form
  // the not-yet-generated schemas still return both resolve. An unrecognised score
  // drops the row from every aggregate, so this must accept both spellings.
  return COMPLEXITY_SCORE_MAP[score.toLowerCase().trim().replace(/_/g, ' ')];
}

function complexityScoreLabel(avg: number): string {
  if (avg < 1.5) return 'Slightly Complex';
  if (avg < 2.5) return 'Moderately Complex';
  if (avg < 3.5) return 'Very Complex';
  return 'Exceedingly Complex';
}

/** Stub — returns hard-coded insights. Replace with real logic later. */
function generateInsights(): string[] {
  return [
    'Review texts marked as Off Target — they may need content revision or grade-level adjustment before distribution.',
    'Texts evaluated as Adjacent may benefit from light scaffolding strategies such as vocabulary pre-teaching.',
    'Higher grade bands tend to show greater text complexity. Consider whether complexity aligns with instructional goals.',
  ];
}

// ---- Shared grouping utility ----

function groupResultsByRow(results: BatchResult[]): Map<number, BatchResult[]> {
  const grouped = new Map<number, BatchResult[]>();
  for (const result of results) {
    if (!grouped.has(result.rowIndex)) {
      grouped.set(result.rowIndex, []);
    }
    grouped.get(result.rowIndex)!.push(result);
  }
  return grouped;
}

// ---- CSV Formatter ----

function formatEvaluatorPrefix(evaluatorId: string): string {
  const slug = evaluatorId.includes('.') ? evaluatorId.split('.').pop()! : evaluatorId;
  return slug.replace(/-/g, '_');
}

function escapeCSV(field: string): string {
  if (field.includes(',') || field.includes('"') || field.includes('\n')) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
}

export function formatAsCSV(output: BatchOutput): string {
  if (output.results.length === 0) {
    return '';
  }

  const groupedByRow = groupResultsByRow(output.results);
  const evaluatorIds = Array.from(new Set(output.results.map(r => r.evaluatorId))).sort();
  const firstResult = output.results[0];
  const originalColumns = Object.keys(firstResult.originalRow);

  const evaluatorColumns: string[] = [];
  for (const evalId of evaluatorIds) {
    const prefix = formatEvaluatorPrefix(evalId);
    evaluatorColumns.push(`${prefix}_score`);
    evaluatorColumns.push(`${prefix}_reasoning`);
    evaluatorColumns.push(`${prefix}_status`);
  }
  const headers = [...originalColumns, ...evaluatorColumns];

  const rows: string[][] = [];
  const sortedRowIndices = Array.from(groupedByRow.keys()).sort((a, b) => a - b);

  for (const rowIndex of sortedRowIndices) {
    const resultsForRow = groupedByRow.get(rowIndex)!;
    const firstResultForRow = resultsForRow[0];

    const originalValues = originalColumns.map(col =>
      escapeCSV(String(firstResultForRow.originalRow[col] || ''))
    );

    const evaluatorValues: string[] = [];
    for (const evalId of evaluatorIds) {
      const result = resultsForRow.find(r => r.evaluatorId === evalId);
      if (result) {
        evaluatorValues.push(result.status === 'success' ? escapeCSV(result.score || '') : '');
        evaluatorValues.push(result.status === 'success'
          ? escapeCSV(result.reasoning || '')
          : escapeCSV(result.error || ''));
        evaluatorValues.push(result.status);
      } else {
        evaluatorValues.push('', '', 'not_run');
      }
    }

    rows.push([...originalValues, ...evaluatorValues]);
  }

  return [headers, ...rows].map(row => row.join(',')).join('\n');
}

// ---- JSON Formatter ----

export interface ReportMeta {
  csvPath: string;
  groupId: string;
  reportId: string;
  generatedAt: Date;
  totalInputRows: number;
}

/**
 * Generic machine-readable output for the text-complexity family: one entry per
 * (row, evaluator) with score/reasoning plus the untouched original row.
 */
export function formatAsJSON(output: BatchOutput, meta: ReportMeta): string {
  return JSON.stringify(
    {
      meta: {
        reportId: meta.reportId,
        family: meta.groupId,
        generatedAt: meta.generatedAt.toISOString(),
        sourcePath: meta.csvPath,
        totalInputRows: meta.totalInputRows,
      },
      summary: output.summary,
      results: output.results
        .slice()
        .sort((a, b) => a.rowIndex - b.rowIndex || a.evaluatorId.localeCompare(b.evaluatorId))
        .map((r) => ({
          rowIndex: r.rowIndex,
          evaluatorId: r.evaluatorId,
          status: r.status,
          score: r.score ?? null,
          reasoning: r.reasoning ?? null,
          error: r.error ?? null,
          originalRow: r.originalRow,
        })),
    },
    null,
    2,
  );
}

// ---- HTML Formatter ----

export function formatAsHTML(output: BatchOutput, meta: ReportMeta): string {
  const { results } = output;
  const byRow = groupResultsByRow(results);
  const allRowIndices = Array.from(byRow.keys()).sort((a, b) => a - b);

  const allEvaluatorIds = Array.from(new Set(results.map(r => r.evaluatorId))).sort();
  const hasGLA = allEvaluatorIds.includes(GLA_EVALUATOR_ID);
  const complexityIds = allEvaluatorIds.filter(id => id !== GLA_EVALUATOR_ID);

  // ---- Snapshot ----
  let processedRows = 0;
  let erroredRows = 0;
  for (const rowResults of byRow.values()) {
    if (rowResults.some(r => r.status === 'error')) erroredRows++;
    else processedRows++;
  }

  // ---- GLA stats ----
  const glaCounts = { onBand: 0, adjacent: 0, offTarget: 0 };
  const rowGLAStatus = new Map<number, {
    status: 'on-band' | 'adjacent' | 'off-target';
    band: string;
    reasoning: string;
  }>();

  if (hasGLA) {
    for (const [rowIndex, rowResults] of byRow) {
      const glaResult = rowResults.find(r => r.evaluatorId === GLA_EVALUATOR_ID);
      if (glaResult && glaResult.status === 'success' && glaResult.score) {
        const status = getGLAStatus(glaResult.gradeLevel, glaResult.score);
        rowGLAStatus.set(rowIndex, { status, band: glaResult.score, reasoning: glaResult.reasoning || '' });
        if (status === 'on-band') glaCounts.onBand++;
        else if (status === 'adjacent') glaCounts.adjacent++;
        else glaCounts.offTarget++;
      }
    }
  }

  const glaTotal = glaCounts.onBand + glaCounts.adjacent + glaCounts.offTarget;
  const pct = (n: number) => glaTotal > 0 ? Math.round((n / glaTotal) * 100) : 0;

  // ---- Complexity stats per evaluator ----
  const complexityStats = complexityIds.map(evalId => {
    const scores: number[] = [];
    const distribution: [number, number, number, number] = [0, 0, 0, 0];

    for (const rowResults of byRow.values()) {
      const r = rowResults.find(x => x.evaluatorId === evalId);
      if (r && r.status === 'success' && r.score) {
        const num = complexityToNumeric(r.score);
        if (num !== undefined) {
          scores.push(num);
          distribution[num - 1]++;
        }
      }
    }

    const avg = scores.length > 0 ? scores.reduce((a, b) => a + b, 0) / scores.length : 0;
    return {
      evaluatorId: evalId,
      name: evaluatorDisplayName(evalId),
      average: Math.round(avg * 10) / 10,
      label: avg > 0 ? complexityScoreLabel(avg) : 'N/A',
      distribution,
    };
  });

  // ---- Grade band distribution (GLA status per input grade band) ----
  const bandDist = GRADE_BANDS.map(() => ({ onBand: 0, adjacent: 0, offTarget: 0, total: 0 }));

  for (const [rowIndex, rowResults] of byRow) {
    const firstResult = rowResults[0];
    if (!firstResult) continue;
    const bandIdx = gradeToBandIndex(firstResult.gradeLevel);
    if (bandIdx === -1) continue;

    const glaStatus = rowGLAStatus.get(rowIndex);
    if (glaStatus) {
      bandDist[bandIdx].total++;
      if (glaStatus.status === 'on-band') bandDist[bandIdx].onBand++;
      else if (glaStatus.status === 'adjacent') bandDist[bandIdx].adjacent++;
      else bandDist[bandIdx].offTarget++;
    }
  }

  // ---- Complexity heatmap: avg score per [grade band][evaluator] ----
  const hmSums: number[][] = GRADE_BANDS.map(() => complexityIds.map(() => 0));
  const hmCounts: number[][] = GRADE_BANDS.map(() => complexityIds.map(() => 0));

  for (const rowResults of byRow.values()) {
    const firstResult = rowResults[0];
    if (!firstResult) continue;
    const bandIdx = gradeToBandIndex(firstResult.gradeLevel);
    if (bandIdx === -1) continue;

    complexityIds.forEach((evalId, evalIdx) => {
      const r = rowResults.find(x => x.evaluatorId === evalId);
      if (r && r.status === 'success' && r.score) {
        const num = complexityToNumeric(r.score);
        if (num !== undefined) {
          hmSums[bandIdx][evalIdx] += num;
          hmCounts[bandIdx][evalIdx]++;
        }
      }
    });
  }

  const heatmapValues: (number | null)[][] = GRADE_BANDS.map((_, bi) =>
    complexityIds.map((_, ei) => {
      const count = hmCounts[bi][ei];
      return count > 0 ? Math.round((hmSums[bi][ei] / count) * 10) / 10 : null;
    })
  );

  // ---- Full results rows ----
  const firstRowResults = allRowIndices.length > 0 ? (byRow.get(allRowIndices[0]) ?? []) : [];
  const originalColumns = firstRowResults.length > 0 ? Object.keys(firstRowResults[0].originalRow) : [];

  const fullResultsRows = allRowIndices.map(rowIndex => {
    const rowResults = byRow.get(rowIndex)!;
    const firstResult = rowResults[0];
    const row: Record<string, string> = {};

    for (const col of originalColumns) {
      row[col] = String(firstResult.originalRow[col] ?? '');
    }

    const glaStatus = rowGLAStatus.get(rowIndex);
    const glaLabels = { 'on-band': 'On Band', 'adjacent': 'Adjacent', 'off-target': 'Off Target' } as const;
    row['__gla_status'] = glaStatus ? glaLabels[glaStatus.status] : (hasGLA ? 'Error' : '');
    row['__gla_band'] = glaStatus?.band ?? '';
    row['__gla_reasoning'] = glaStatus?.reasoning ?? '';

    for (const evalId of complexityIds) {
      const r = rowResults.find(x => x.evaluatorId === evalId);
      const prefix = `__${formatEvaluatorPrefix(evalId)}`;
      row[`${prefix}_score`] = r?.status === 'success' ? (r.score ?? '') : (r?.status === 'error' ? 'Error' : '');
      row[`${prefix}_reasoning`] = r?.status === 'success' ? (r.reasoning ?? '') : (r?.error ?? '');
    }

    return row;
  });

  // ---- Assemble report data ----
  const reportData = {
    meta: {
      reportId: meta.reportId,
      generatedAt: meta.generatedAt.toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric',
        hour: 'numeric', minute: '2-digit', hour12: true,
      }),
      csvPath: meta.csvPath,
      groupId: meta.groupId,
      evaluatorIds: allEvaluatorIds,
      evaluatorNames: allEvaluatorIds.map(evaluatorDisplayName),
      totalRows: meta.totalInputRows,
      processedRows,
      erroredRows,
    },
    gradeLevelStats: {
      onBand: glaCounts.onBand,
      adjacent: glaCounts.adjacent,
      offTarget: glaCounts.offTarget,
      onBandPct: pct(glaCounts.onBand),
      adjacentPct: pct(glaCounts.adjacent),
      offTargetPct: pct(glaCounts.offTarget),
      hasData: glaTotal > 0,
    },
    complexityStats,
    gradeBandDistribution: {
      bands: [...GRADE_BANDS],
      data: bandDist,
    },
    complexityHeatmap: {
      bands: [...GRADE_BANDS],
      evaluators: complexityIds.map(evaluatorDisplayName),
      evaluatorIds: complexityIds,
      values: heatmapValues,
    },
    insights: generateInsights(),
    fullResults: {
      originalColumns,
      hasGLA,
      complexityEvaluators: complexityIds.map(id => ({
        evaluatorId: id,
        name: evaluatorDisplayName(id),
        prefix: formatEvaluatorPrefix(id),
      })),
      rows: fullResultsRows,
    },
  };

  // Inject serialized data into the template.
  // Unicode-escape < > & so the JSON is safe inside a <script> tag even if
  // the data contains HTML-like strings (prevents </script> injection).
  const safeJson = JSON.stringify(reportData)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026');

  const INJECTION_MARKER = 'var REPORT_DATA = null; // __REPLACED_BY_FORMATTER__';
  if (!reportTemplate.includes(INJECTION_MARKER)) {
    throw new Error('Report template injection marker not found — template may be corrupted');
  }

  return reportTemplate.replace(INJECTION_MARKER, `var REPORT_DATA = ${safeJson};`);
}
