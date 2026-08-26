import pLimit from 'p-limit';
import {
  ConfigurationError,
  StandardNotFoundError,
  AuthenticationError,
  InputValidationError,
  KnowledgeGraphError,
} from '../errors.js';
import { KnowledgeGraphClient, normalizeStatementCode, STANDARD_SEARCH_LIMIT } from './client.js';
import { Jurisdiction, type AcademicStandard, type StandardInfo } from './types.js';

/** From evals/standards/math-question-alignment/input_schema.json. */
const MAX_STATEMENT_CODE_LENGTH = 50;

/** Rejects locally what the KG cannot usefully answer. Returns null when the code is plausible. */
function localCodeProblem(normalizedCode: string): string | null {
  if (normalizedCode === '') return 'Statement code is empty';
  if (normalizedCode.length > MAX_STATEMENT_CODE_LENGTH) {
    return `Statement code exceeds ${MAX_STATEMENT_CODE_LENGTH} characters — check for a mis-split column`;
  }
  return null;
}

export interface StandardsCatalogConfig {
  /** Learning Commons platform API key, used for Knowledge Graph access. */
  platformApiKey: string;
  /**
   * Default subject filter for all lookups (e.g. 'Mathematics'). No default,
   * because omitting it makes the result subject-dependent rather than wrong in a
   * predictable way: Multi-State returns standards across subjects, while another
   * jurisdiction resolves to whichever of its per-subject frameworks comes first.
   */
  academicSubject?: string;
  /** Max concurrent Knowledge Graph requests. Defaults to 20. */
  concurrency?: number;
}

export interface StandardsLookupOptions {
  /** Defaults to Multi-State (Common Core). */
  jurisdiction?: Jurisdiction;
  /** Overrides the catalog-level academicSubject for this call. */
  academicSubject?: string;
}

/**
 * A statement code does not always identify one standard: a jurisdiction may reuse
 * the same code across courses. These outcomes distinguish the cases a caller must
 * act on differently.
 *
 * - `resolved` — exactly one candidate carries learning components.
 * - `no-learning-components` — the code exists but nothing is authored against it,
 *   so an evaluation would score 0 of 0. Not a failure, and not non-alignment.
 * - `ambiguous` — several candidates carry *different* learning components; the
 *   caller must pick a `uuid` from `candidates`.
 * - `not-found` — no such code in this jurisdiction.
 * - `unchecked` — no verdict could be reached, so this says nothing about the code.
 *   Either the lookup failed (network, 429, 5xx) or it succeeded but its answer is
 *   not supportable — a candidate list capped at the search limit where none of the
 *   visible candidates had learning components. Check `error` for which.
 */
export type CodeResolutionStatus =
  | 'resolved'
  | 'no-learning-components'
  | 'ambiguous'
  | 'not-found'
  | 'unchecked';

/** One standard a code matched, with the learning components attached to it. */
export interface StandardCandidate extends StandardInfo {
  learningComponentCount: number;
}

export interface CodeValidation {
  /** The code exactly as supplied by the caller. */
  input: string;
  /** The KG's spelling when resolved; otherwise the normalized form. */
  statementCode: string;
  /** Canonical lookup key — dedupe and join on this. */
  normalizedCode: string;
  status: CodeResolutionStatus;
  /** The chosen standard, when `status` is `resolved`. */
  uuid?: string;
  /** Echoed so a wrong-but-resolvable code is visible to the user. */
  description?: string;
  /**
   * Populated when `status` is `ambiguous`: every candidate with learning
   * components, so the caller can choose one by `uuid`.
   */
  candidates?: StandardCandidate[];
  /** True when the candidate list may have been cut off at the search limit. */
  truncated?: boolean;
  /** Present unless `status` is `resolved`. */
  error?: string;
}

/**
 * Read-only access to the Learning Commons academic standards catalog.
 *
 * Wraps the Knowledge Graph client so callers get standards lookup without
 * depending on the client's cache or concurrency internals.
 */
export class StandardsCatalog {
  private readonly kg: KnowledgeGraphClient;
  private readonly academicSubject?: string;
  private readonly concurrency: number;

  constructor(config: StandardsCatalogConfig) {
    if (!config.platformApiKey?.trim()) {
      throw new ConfigurationError('platformApiKey is required to access the standards catalog.');
    }
    const concurrency = config.concurrency ?? 20;
    if (!Number.isInteger(concurrency) || concurrency < 1) {
      throw new ConfigurationError(`concurrency must be a positive integer, received ${config.concurrency}`);
    }
    // Whitespace would be sent as a subject filter and silently match nothing.
    const academicSubject = config.academicSubject?.trim();

    this.concurrency = concurrency;
    this.kg = new KnowledgeGraphClient(config.platformApiKey, concurrency);
    this.academicSubject = academicSubject || undefined;
  }

  /** All instructional standards for a grade, across every result page. */
  listStandards(grade: string, opts?: StandardsLookupOptions): Promise<AcademicStandard[]> {
    return this.kg.getStandardsByGrade(grade, {
      jurisdiction: opts?.jurisdiction ?? Jurisdiction.MultiState,
      academicSubject: opts?.academicSubject ?? this.academicSubject,
    });
  }

  /**
   * Resolve a single statement code. Throws `InputValidationError` for a code the KG
   * cannot answer for, and `StandardNotFoundError` when it does not exist.
   */
  // async so a rejected code rejects rather than throwing synchronously, which
  // would force callers into both try/catch and .catch().
  async getStandard(statementCode: string, opts?: StandardsLookupOptions): Promise<StandardInfo> {
    const problem = localCodeProblem(normalizeStatementCode(statementCode));
    if (problem) throw new InputValidationError(problem);

    return this.kg.getStandardInfo(statementCode, {
      jurisdiction: opts?.jurisdiction ?? Jurisdiction.MultiState,
      academicSubject: opts?.academicSubject ?? this.academicSubject,
    });
  }

  /**
   * Resolve a code to the one standard worth evaluating, discarding candidates with
   * no learning components.
   *
   * Candidates sharing an identical learning-component set are interchangeable, so
   * any of them resolves. Only differing sets are genuinely `ambiguous`; comparing
   * descriptions is not sufficient, since codes exist whose candidates read
   * identically but carry different components.
   *
   * Throws only for failures that doom every lookup (`AuthenticationError`,
   * `ConfigurationError`); anything else yields `unchecked`.
   */
  async resolveStandard(
    statementCode: string,
    opts?: StandardsLookupOptions,
  ): Promise<CodeValidation> {
    const normalized = normalizeStatementCode(statementCode);
    const base = { input: statementCode, statementCode: normalized, normalizedCode: normalized };

    const problem = localCodeProblem(normalized);
    if (problem) return { ...base, status: 'not-found', error: problem };

    const lookup = {
      jurisdiction: opts?.jurisdiction ?? Jurisdiction.MultiState,
      academicSubject: opts?.academicSubject ?? this.academicSubject,
    };

    try {
      const found = await this.kg.getStandardCandidates(normalized, lookup);
      const truncated = found.length === STANDARD_SEARCH_LIMIT;

      const resolved = await Promise.all(
        found.map(async (candidate) => {
          const components = await this.kg.getLearningComponents(candidate.uuid);
          return {
            candidate: { ...candidate, learningComponentCount: components.length },
            signature: components.map((c) => c.identifier).sort().join('|'),
          };
        }),
      );

      const populated = resolved.filter((r) => r.candidate.learningComponentCount > 0);
      const withComponents = populated.map((r) => r.candidate);
      const distinctSets = new Set(populated.map((r) => r.signature));

      if (withComponents.length === 0) {
        // A truncated list cannot support the definitive claim: an unseen candidate
        // beyond the cap may well carry components.
        if (truncated) {
          return {
            ...base,
            statementCode: found[0].statementCode,
            status: 'unchecked',
            truncated: true,
            error:
              `None of the first ${STANDARD_SEARCH_LIMIT} matches have learning components, ` +
              'and the candidate list was capped, so others may',
          };
        }
        return {
          ...base,
          statementCode: found[0].statementCode,
          status: 'no-learning-components',
          uuid: found[0].uuid,
          ...(found[0].description !== undefined ? { description: found[0].description } : {}),
          error: 'No learning components are authored against this standard',
        };
      }

      if (withComponents.length === 1 || distinctSets.size === 1) {
        const chosen = withComponents[0];
        return {
          ...base,
          statementCode: chosen.statementCode,
          status: 'resolved',
          uuid: chosen.uuid,
          ...(chosen.description !== undefined ? { description: chosen.description } : {}),
          ...(truncated ? { truncated: true } : {}),
        };
      }

      // One representative per distinct component set: candidates sharing a set are
      // interchangeable, so offering all of them would overstate the real choice.
      const bySignature = new Map<string, StandardCandidate>();
      for (const { signature, candidate } of populated) {
        if (!bySignature.has(signature)) bySignature.set(signature, candidate);
      }
      const choices = [...bySignature.values()];

      return {
        ...base,
        statementCode: choices[0].statementCode,
        status: 'ambiguous',
        candidates: choices,
        ...(truncated ? { truncated: true } : {}),
        error:
          `Matched ${choices.length} standards with different learning components — ` +
          'pass a uuid to choose one',
      };
    } catch (err) {
      if (err instanceof StandardNotFoundError) {
        return { ...base, status: 'not-found', error: err.message };
      }
      if (err instanceof AuthenticationError || err instanceof ConfigurationError) {
        throw err;
      }
      // A 400 means the request itself was malformed. `jurisdiction` is enum-typed,
      // so the realistic cause is an unrecognised `academicSubject` — which fails
      // identically for every code. Not fatal, because a 400 could still be specific
      // to one code, and aborting would discard every other result.
      if (err instanceof KnowledgeGraphError && err.statusCode === 400) {
        return {
          ...base,
          status: 'unchecked',
          error:
            'Knowledge Graph rejected the request as malformed (400) — check academicSubject ' +
            `and jurisdiction, which fail for every code when wrong. ${err.message}`,
        };
      }
      return { ...base, status: 'unchecked', error: err instanceof Error ? err.message : String(err) };
    }
  }

  /**
   * Check many codes at once. Returns one result per distinct normalized code, in
   * first-seen input order; repeats cost one request.
   *
   * Only `AuthenticationError` and `ConfigurationError` throw, since those doom
   * every other lookup identically. Other failures yield `'unchecked'`.
   */
  async validateCodes(
    statementCodes: string[],
    opts?: StandardsLookupOptions,
  ): Promise<CodeValidation[]> {
    // First-seen input wins, so the reported `input` matches what the user wrote.
    const distinct = new Map<string, string>();
    for (const code of statementCodes) {
      const normalized = normalizeStatementCode(code);
      if (!distinct.has(normalized)) distinct.set(normalized, code);
    }

    // A bad key fails every code identically, so stop scheduling once one throws.
    // The check must sit behind the limiter: without it every lookup would already
    // have been issued before the first rejection arrived.
    const limit = pLimit(this.concurrency);
    let fatal: unknown;

    const settled = await Promise.allSettled(
      [...distinct.values()].map((input) =>
        limit(async (): Promise<CodeValidation> => {
          if (fatal !== undefined) throw fatal;
          try {
            return { ...(await this.resolveStandard(input, opts)), input };
          } catch (err) {
            fatal = err;
            throw err;
          }
        }),
      ),
    );

    const rejected = settled.find((s): s is PromiseRejectedResult => s.status === 'rejected');
    if (rejected) throw rejected.reason;

    return (settled as PromiseFulfilledResult<CodeValidation>[]).map((s) => s.value);
  }
}
