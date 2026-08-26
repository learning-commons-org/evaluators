import { Provider } from '../../evaluators/base.js';
import type { ModelOverride, TelemetryOptions } from '../../evaluators/base.js';
import type { LLMProvider } from '../../providers/index.js';

/**
 * A credential an evaluator family needs to run. Provider values match
 * {@link Provider}; `'learning-commons'` is the Learning Commons platform key used for
 * Knowledge Graph access (distinct from any LLM provider key).
 */
export type KeyKind = Provider | 'learning-commons';

/**
 * Declares one canonical input column a family consumes. `aliases` are
 * additional CSV header names (case-insensitive) that map onto `name`.
 * When a column is absent and `default` is set, the default is applied.
 */
export interface ColumnSpec {
  name: string;
  aliases?: string[];
  required: boolean;
  default?: string;
}

/** A single evaluator within a family (the unit of member-selection). */
export interface FamilyMember {
  id: string;
  name: string;
}

/**
 * A row after CSV parsing + column normalization: canonical columns (with
 * defaults applied) plus the untouched original row for passthrough into
 * outputs.
 */
export interface FamilyRow {
  rowIndex: number;
  columns: Record<string, string>;
  originalRow: Record<string, unknown>;
}

/** Credentials and knobs handed to a family when building a runner. */
export interface FamilyRunContext {
  googleApiKey?: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  learningCommonsApiKey?: string;
  maxRetries?: number;
  telemetry?: boolean | TelemetryOptions;
  modelOverride?: ModelOverride;
  llmProvider?: LLMProvider;
  concurrency?: number;
  kgConcurrency?: number;
}

/** The structured result of running one member against one row. */
export interface TaskOutcome {
  /** Human-facing scalar score (e.g. a complexity band, or "3/5" aligned). */
  score: string;
  /** Short reasoning/summary; may be empty for structured families. */
  reasoning: string;
  /** Full structured verdict, for families whose output isn't scalar. */
  payload?: unknown;
}

/**
 * A family instance bound to a specific set of selected members and
 * credentials. Owns *how* to invoke each evaluator; the BatchEvaluator owns
 * orchestration (concurrency, cancellation, timing, error handling).
 */
export interface FamilyRunner {
  /** The members this runner will execute (post member-selection). */
  members: FamilyMember[];
  runTask(row: FamilyRow, memberId: string): Promise<TaskOutcome>;
}

/**
 * An evaluator family: a group of evaluators that share an input contract,
 * credential needs, and output/report shape. The unit of selection exposed to
 * batch users. Adding a new family (e.g. feedback) requires no core changes.
 */
export interface EvaluatorFamily {
  id: string;
  name: string;
  description: string;
  members: FamilyMember[];
  columns: ColumnSpec[];
  /** Maximum input rows allowed for this family. */
  maxInputRows: number;
  /** Credentials required given the selected members and any model override. */
  requiredKeys(selectedMemberIds: string[], modelOverride?: ModelOverride): KeyKind[];
  /** Build a runner for the selected members (empty/undefined = all members). */
  createRunner(ctx: FamilyRunContext, selectedMemberIds?: string[]): FamilyRunner;
}

// --- Column normalization -------------------------------------------------

function matchesSpec(headerKey: string, spec: ColumnSpec): boolean {
  const candidates = [spec.name, ...(spec.aliases ?? [])].map((s) => s.toLowerCase().trim());
  return candidates.includes(headerKey.toLowerCase().trim());
}

/**
 * Resolve a spec's value from a raw row. Candidates are tried in priority order
 * — canonical name first, then aliases — and the first *non-empty* match wins,
 * so a present-but-empty alias can't shadow a populated canonical column. Falls
 * back to the first (possibly empty) match if nothing is non-empty.
 */
function resolveColumnValue(
  rawColumns: Record<string, string>,
  spec: ColumnSpec,
): string | undefined {
  const headerKeys = Object.keys(rawColumns);
  let firstMatch: string | undefined;
  for (const candidate of [spec.name, ...(spec.aliases ?? [])]) {
    const target = candidate.toLowerCase().trim();
    const key = headerKeys.find((k) => k.toLowerCase().trim() === target);
    if (key === undefined) continue;
    const value = rawColumns[key];
    if (value !== undefined && value !== '') return value;
    if (firstMatch === undefined) firstMatch = value;
  }
  return firstMatch;
}

/**
 * Fail fast if the CSV is missing a required column entirely (header-level).
 * Per-row empty values are handled during {@link normalizeRow}.
 */
export function validateRequiredColumns(family: EvaluatorFamily, headerKeys: string[]): void {
  const missing = family.columns
    .filter((spec) => spec.required && !headerKeys.some((h) => matchesSpec(h, spec)))
    .map((spec) => spec.name);
  if (missing.length > 0) {
    throw new Error(
      `CSV is missing required column(s) for family "${family.id}": ${missing.join(', ')} ` +
        `(aliases are accepted; see the family's column spec).`,
    );
  }
}

/**
 * Map a raw row's columns onto the family's canonical column names, applying
 * defaults and enforcing per-row required values. Throws for a row that lacks a
 * required value with no default.
 */
export function normalizeRow(
  raw: { rowIndex: number; columns: Record<string, string>; originalRow: Record<string, unknown> },
  family: EvaluatorFamily,
): FamilyRow {
  const columns: Record<string, string> = {};
  for (const spec of family.columns) {
    let value = resolveColumnValue(raw.columns, spec);
    if ((value === undefined || value === '') && spec.default !== undefined) {
      value = spec.default;
    }
    if ((value === undefined || value === '') && spec.required) {
      throw new Error(`Row ${raw.rowIndex}: missing required value for column "${spec.name}"`);
    }
    if (value !== undefined) columns[spec.name] = value;
  }
  return { rowIndex: raw.rowIndex, columns, originalRow: raw.originalRow };
}

/** Resolve requested member ids against a family, defaulting to all members. */
export function resolveMembers(
  family: EvaluatorFamily,
  selectedMemberIds?: string[],
): FamilyMember[] {
  if (!selectedMemberIds || selectedMemberIds.length === 0) return family.members;
  const byId = new Map(family.members.map((m) => [m.id, m]));
  const resolved: FamilyMember[] = [];
  for (const id of selectedMemberIds) {
    const member = byId.get(id);
    if (!member) {
      throw new Error(
        `Unknown evaluator "${id}" for family "${family.id}". ` +
          `Available: ${family.members.map((m) => m.id).join(', ')}`,
      );
    }
    resolved.push(member);
  }
  return resolved;
}

export { Provider };
