import type { BatchOutput, BatchResult } from '../types.js';
import type { StandardsVerdict } from './standards.js';
import standardsReportTemplate from './standards-report.html';

/** Metadata shared by every output projection. */
export interface StandardsOutputMeta {
  reportId: string;
  generatedAt: Date;
  sourcePath: string;
  totalInputRows: number;
}

/**
 * One flattened verdict per input row. `learningComponents` is preserved in
 * full for the JSON/HTML views; the CSV flattens the roll-ups and carries the
 * per-component detail as an embedded JSON string so it stays joinable.
 */
interface StandardsRow {
  rowIndex: number;
  id: string;
  grade: string;
  statementCode: string;
  jurisdiction: string;
  question: string;
  status: 'success' | 'error';
  alignedCount: number | null;
  totalCount: number | null;
  error: string | null;
  learningComponents: StandardsVerdict['learningComponents'];
  originalRow: Record<string, unknown>;
}

function toRow(result: BatchResult): StandardsRow {
  const verdict = result.payload as StandardsVerdict | undefined;
  const original = result.originalRow ?? {};
  const idValue = original.id ?? original.item_id ?? '';
  return {
    rowIndex: result.rowIndex,
    id: String(idValue),
    grade: result.grade ?? '',
    statementCode: verdict?.statementCode ?? String(original.statementCode ?? original.ccss_standard ?? ''),
    jurisdiction: verdict?.jurisdiction ?? '',
    question: verdict?.question ?? result.text ?? '',
    status: result.status,
    alignedCount: verdict ? verdict.alignedCount : null,
    totalCount: verdict ? verdict.totalCount : null,
    error: result.status === 'error' ? result.error ?? 'Unknown error' : null,
    learningComponents: verdict?.learningComponents ?? [],
    originalRow: original,
  };
}

function collectRows(output: BatchOutput): StandardsRow[] {
  return output.results.map(toRow).sort((a, b) => a.rowIndex - b.rowIndex);
}

// --- JSON ------------------------------------------------------------------

/**
 * Machine-readable verdicts for downstream analysis (flag-rate, coverage). Each
 * item carries the full per-component detail plus the untouched `originalRow`,
 * so results join back to the source corpus on any column.
 */
export function formatStandardsJSON(output: BatchOutput, meta: StandardsOutputMeta): string {
  const rows = collectRows(output);
  return JSON.stringify(
    {
      meta: {
        reportId: meta.reportId,
        family: 'math-standards-alignment',
        generatedAt: meta.generatedAt.toISOString(),
        sourcePath: meta.sourcePath,
        totalInputRows: meta.totalInputRows,
      },
      summary: output.summary,
      items: rows.map((r) => ({
        rowIndex: r.rowIndex,
        id: r.id,
        grade: r.grade,
        statementCode: r.statementCode,
        jurisdiction: r.jurisdiction,
        question: r.question,
        status: r.status,
        alignedCount: r.alignedCount,
        totalCount: r.totalCount,
        error: r.error,
        learningComponents: r.learningComponents,
        originalRow: r.originalRow,
      })),
    },
    null,
    2,
  );
}

// --- CSV -------------------------------------------------------------------

function escapeCSV(field: string): string {
  if (/[",\n\r]/.test(field)) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
}

/**
 * Flat, joinable CSV: passthrough of every original column, then the verdict
 * roll-ups. Per-component detail rides along as a JSON string so no data is
 * lost while the file stays spreadsheet-friendly. Verdict columns that would
 * collide with an existing source column are `verdict_`-prefixed so joins stay
 * unambiguous.
 */
export function formatStandardsCSV(output: BatchOutput): string {
  const rows = collectRows(output);
  if (rows.length === 0) return '';

  const originalColumns = Object.keys(rows[0].originalRow);
  const lowerOriginal = new Set(originalColumns.map((c) => c.toLowerCase()));
  const verdictFields = [
    'statement_code',
    'jurisdiction',
    'aligned_count',
    'total_count',
    'aligned_ratio',
    'status',
    'error',
    'learning_components_json',
  ];
  const verdictColumns = verdictFields.map((name) =>
    lowerOriginal.has(name.toLowerCase()) ? `verdict_${name}` : name,
  );
  const headers = [...originalColumns, ...verdictColumns].map(escapeCSV);

  const lines = rows.map((r) => {
    const originalValues = originalColumns.map((col) => escapeCSV(String(r.originalRow[col] ?? '')));
    const ratio =
      r.alignedCount !== null && r.totalCount !== null && r.totalCount > 0
        ? (r.alignedCount / r.totalCount).toFixed(3)
        : '';
    const verdictValues = [
      escapeCSV(r.statementCode),
      escapeCSV(r.jurisdiction),
      r.alignedCount ?? '',
      r.totalCount ?? '',
      ratio,
      r.status,
      escapeCSV(r.error ?? ''),
      escapeCSV(JSON.stringify(r.learningComponents)),
    ];
    return [...originalValues, ...verdictValues].join(',');
  });

  return [headers.join(','), ...lines].join('\n');
}

// --- HTML ------------------------------------------------------------------

const INJECTION_MARKER = 'var REPORT_DATA = null; // __REPLACED_BY_FORMATTER__';

/**
 * Self-contained verdict browser: per-item aligned/total with expandable
 * per-component reasoning/feedback, filterable by standard and grade. Reports
 * verdicts only — no flag-rate/coverage aggregates (that is interpretation,
 * done downstream from the JSON).
 */
export function formatStandardsHTML(output: BatchOutput, meta: StandardsOutputMeta): string {
  const rows = collectRows(output);
  const reportData = {
    meta: {
      reportId: meta.reportId,
      generatedAt: meta.generatedAt.toLocaleString('en-US', {
        month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric', minute: '2-digit', hour12: true,
      }),
      sourcePath: meta.sourcePath,
      totalInputRows: meta.totalInputRows,
      successful: output.summary.successful,
      failed: output.summary.failed,
    },
    items: rows,
  };

  const safeJson = JSON.stringify(reportData)
    .replace(/</g, '\\u003c')
    .replace(/>/g, '\\u003e')
    .replace(/&/g, '\\u0026');

  if (!standardsReportTemplate.includes(INJECTION_MARKER)) {
    throw new Error('Standards report template injection marker not found — template may be corrupted');
  }
  return standardsReportTemplate.replace(INJECTION_MARKER, `var REPORT_DATA = ${safeJson};`);
}
