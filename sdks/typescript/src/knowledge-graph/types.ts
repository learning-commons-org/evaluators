import { ValidationError } from '../errors.js';

export interface AcademicStandard {
  caseIdentifierUUID: string;
  statementCode: string;
  description: string;
  statementType: string;
  normalizedStatementType: string;
  /** Grade levels this standard applies to (e.g. ["3"] or ["K"]) */
  gradeLevel: string[];
}

export interface LearningComponentRaw {
  identifier: string;
  description: string | null;
  author?: string;
  provider?: string;
}

export interface LearningComponent {
  description: string;
}

export interface GetStandardsOptions {
  /** Filter out Mathematical Practice (MP) standards. Default: true */
  excludeMP?: boolean;
}

export interface StandardInfo {
  uuid: string;
  /** Human-readable description from the KG search response. May be absent for some standards. */
  description?: string;
}

export interface StandardsRepository {
  getStandardInfo(statementCode: string): Promise<StandardInfo>;
  getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]>;
  getStandardsByGrade(grade: string, options?: GetStandardsOptions): Promise<AcademicStandard[]>;
}

const VALID_GRADES = new Set(['K', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']);

export function parseGradeFromStandard(code: string): string {
  const match = code.match(/^(K|\d+)\./);
  if (!match || !VALID_GRADES.has(match[1])) {
    throw new ValidationError(`Cannot parse grade from standard code: "${code}"`);
  }
  return match[1];
}
