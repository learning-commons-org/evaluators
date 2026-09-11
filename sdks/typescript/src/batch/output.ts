import type { BatchOutput } from './types.js';
import { formatAsCSV, formatAsHTML, formatAsJSON, type ReportMeta } from './formatters.js';
import { STANDARDS_FAMILY } from './families/standards.js';
import { QTC_FAMILY } from './families/qtc.js';
import {
  formatStandardsCSV,
  formatStandardsHTML,
  formatStandardsJSON,
} from './families/standards-output.js';

export interface OutputBundle {
  csv: string;
  json: string;
  /** Absent for families with no report of their own — see {@link renderOutputs}. */
  html?: string;
}

/**
 * Render the outputs for a completed batch, choosing the family's projections.
 *
 * CSV and JSON are family-agnostic: original columns plus each evaluator's score,
 * reasoning and status. HTML is not — a report is designed around what a family's
 * verdict means. Standards emits a verdict browser and text-complexity a rubric report;
 * a family without one gets no `html`, rather than a report built for other data.
 */
export function renderOutputs(familyId: string, output: BatchOutput, meta: ReportMeta): OutputBundle {
  if (familyId === STANDARDS_FAMILY.id) {
    const sMeta = {
      reportId: meta.reportId,
      generatedAt: meta.generatedAt,
      sourcePath: meta.csvPath,
      totalInputRows: meta.totalInputRows,
    };
    return {
      csv: formatStandardsCSV(output),
      json: formatStandardsJSON(output, sMeta),
      html: formatStandardsHTML(output, sMeta),
    };
  }
  const bundle: OutputBundle = {
    csv: formatAsCSV(output),
    json: formatAsJSON(output, meta),
  };

  // The text-complexity report averages a four-point complexity scale and charts
  // grade-band alignment, so it only means anything for that family.
  if (familyId === QTC_FAMILY.id) {
    bundle.html = formatAsHTML(output, meta);
  }

  return bundle;
}
