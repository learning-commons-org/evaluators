import { ValidationError } from '../errors.js';

// The generated spec types are in kg-api.d.ts (see npm run generate:kg-types).
// We reference the spec for documentation but keep string-based fields where
// the spec enums don't match the full API response surface (e.g. the spec
// lists normalizedStatementType as "Standard" | "Standard Grouping" | "Other"
// but the API also returns "Mathematical Practice"; gradeLevel enums exclude "HS").

/**
 * An academic standard returned by getStandardsByGrade.
 * Corresponds to StandardsFrameworkItem in the LC KG OpenAPI spec — a subset
 * of the fields needed for alignment evaluation.
 */
export interface AcademicStandard {
  caseIdentifierUUID: string;
  statementCode: string | null | undefined;   // nullable per spec
  description: string | null | undefined;     // nullable per spec
  statementType: string | null | undefined;
  normalizedStatementType: string | null | undefined;
  gradeLevel: string[];
}

/**
 * A learning component used internally for prompt construction.
 * Corresponds to LearningComponent in the LC KG OpenAPI spec.
 * description is filtered to non-null at the repository layer.
 */
export interface LearningComponent {
  description: string;
}

/**
 * Resolved info from a standard code lookup.
 * Assembled from AcademicStandardSearchResult — internal only.
 */
export interface StandardInfo {
  uuid: string;
  description?: string;
}

export interface StandardsRepository {
  getStandardInfo(statementCode: string): Promise<StandardInfo>;
  getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]>;
  getStandardsByGrade(grade: string): Promise<AcademicStandard[]>;
}

// ---------------------------------------------------------------------------
// Utility
// ---------------------------------------------------------------------------

const VALID_GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', 'HS']);

export function parseGradeFromStandard(code: string): string {
  // High school standards use a domain letter + hyphen: HSA-APR.A.1, HSF-BF.A.1, etc.
  if (/^HS[A-Z]-/.test(code)) return 'HS';

  const match = code.match(/^(K|\d+)\./);
  if (!match || !VALID_GRADES.has(match[1])) {
    throw new ValidationError(`Cannot parse grade from standard code: "${code}"`);
  }
  return match[1];
}
