import { ValidationError } from '../errors.js';

// Generated spec types are in kg-api.d.ts — see npm run generate:kg-types.
// We use string for normalizedStatementType and gradeLevel rather than the
// spec's strict enum types so the interfaces remain compatible if the API
// returns values outside the current spec.

/**
 * An academic standard from the LC Knowledge Graph (spec: StandardsFrameworkItem).
 * Subset of fields used for alignment evaluation.
 */
export interface AcademicStandard {
  caseIdentifierUUID: string;
  statementCode: string | null | undefined;
  description: string | null | undefined;
  statementType: string | null | undefined;
  normalizedStatementType: string | null | undefined;
  gradeLevel: string[];
}

/**
 * A learning component from the LC Knowledge Graph.
 * description is guaranteed non-null — nulls are filtered at fetch time.
 */
export interface LearningComponent {
  description: string;
}

/** Resolved info from a standard code lookup. */
export interface StandardInfo {
  uuid: string;
  description?: string;
}

// ---------------------------------------------------------------------------

const VALID_GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);

export function parseGradeFromStandard(code: string): string {
  const match = code.match(/^(K|\d+)\./);
  if (!match || !VALID_GRADES.has(match[1])) {
    throw new ValidationError(`Cannot parse grade from standard code: "${code}"`);
  }
  return match[1];
}
