import type { BatchOutput } from './types.js';
import { formatAsCSV, formatAsHTML, formatAsJSON, type ReportMeta } from './formatters.js';
import { STANDARDS_FAMILY } from './families/standards.js';
import {
  formatStandardsCSV,
  formatStandardsHTML,
  formatStandardsJSON,
} from './families/standards-output.js';

export interface OutputBundle {
  csv: string;
  json: string;
  html: string;
}

/**
 * Render CSV + JSON + HTML for a completed batch, choosing the family's
 * projections. The standards family emits a verdict browser and joinable JSON;
 * every other family uses the text-complexity report shape.
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
  return {
    csv: formatAsCSV(output),
    json: formatAsJSON(output, meta),
    html: formatAsHTML(output, meta),
  };
}
