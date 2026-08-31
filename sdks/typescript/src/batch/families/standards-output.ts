import type { BatchOutput, BatchResult } from '../types.js';
import { STANDARDS_COLUMNS, type StandardsVerdict } from './standards.js';
import standardsReportTemplate from './standards-report.html';
import { injectReportData, toInlineJson } from '../report-injection.js';

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
  gradeLevel: string;
  statementCode: string;
  jurisdiction: string;
  question: string;
  status: 'success' | 'error';
  alignedCount: number | null;
  totalCount: number | null;
  error: string | null;
  learningComponents: StandardsVerdict['learning_components'];
  originalRow: Record<string, unknown>;
}

/**
 * Reads a canonical column, preferring the normalized value and falling back to
 * the untouched source row. The fallback matches case-insensitively against the
 * family's own aliases: a hand-rolled list here would drift from the spec and
 * drop headers the CLI accepts on input (rows that fail normalization carry no
 * canonical columns, so the source row is all that is left).
 */
function column(result: BatchResult, canonical: string): string {
  const normalized = result.columns?.[canonical];
  if (normalized !== undefined && normalized !== '') return normalized;

  const spec = STANDARDS_COLUMNS.find((c) => c.name === canonical);
  const names = [canonical, ...(spec?.aliases ?? [])].map((n) => n.toLowerCase());
  for (const [key, value] of Object.entries(result.originalRow ?? {})) {
    if (names.includes(key.toLowerCase().trim()) && value != null && value !== '') {
      return String(value);
    }
  }
  return '';
}

function toRow(result: BatchResult): StandardsRow {
  const verdict = result.payload as StandardsVerdict | undefined;
  const original = result.originalRow ?? {};
  return {
    rowIndex: result.rowIndex,
    id: column(result, 'id'),
    gradeLevel: result.gradeLevel || column(result, 'grade_level'),
    // Keep context on error rows, which carry no verdict to read from.
    statementCode: verdict?.statement_code ?? column(result, 'statement_code'),
    jurisdiction: verdict?.jurisdiction ?? column(result, 'jurisdiction'),
    question: verdict?.question ?? result.text ?? column(result, 'question'),
    status: result.status,
    alignedCount: verdict ? verdict.aligned_count : null,
    totalCount: verdict ? verdict.total_count : null,
    error: result.status === 'error' ? result.error ?? 'Unknown error' : null,
    learningComponents: verdict?.learning_components ?? [],
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
        gradeLevel: r.gradeLevel,
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

  // Union of source columns across all rows (first-seen order) so a ragged /
  // programmatically-built result set can't silently drop columns.
  const originalColumns: string[] = [];
  const seenOriginal = new Set<string>();
  for (const r of rows) {
    for (const col of Object.keys(r.originalRow)) {
      if (!seenOriginal.has(col)) {
        seenOriginal.add(col);
        originalColumns.push(col);
      }
    }
  }
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

/**
 * Self-contained verdict browser: per-item aligned/total with expandable
 * per-component reasoning/feedback, filterable by standard and grade level. Reports
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

  return injectReportData(standardsReportTemplate, toInlineJson(reportData), 'Standards');
}
