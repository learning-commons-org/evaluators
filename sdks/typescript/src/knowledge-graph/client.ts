import pLimit from 'p-limit';
import createClient, { type Middleware } from 'openapi-fetch';
import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
} from '../errors.js';
import type { AcademicStandard, LearningComponent, LearningComponentSet, StandardInfo } from './types.js';
import type { paths, components } from './kg-api.js';

const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';
const KG_TIMEOUT_MS = 30_000;
const STANDARDS_PAGE_SIZE = 500;
const LC_PAGE_SIZE = 100;
/** The search endpoint's maximum. Explicit because its default is 5, not the cap. */
export const STANDARD_SEARCH_LIMIT = 50;
/** Generous: the largest grade needs 3 pages of 500. */
const MAX_PAGES = 200;

/**
 * Canonical lookup form: trimmed, interior whitespace collapsed, uppercased.
 * Safe because the KG documents statementCode search as "case-insensitive exact
 * match only" (`searchAcademicStandards` in kg-api.d.ts).
 */
export function normalizeStatementCode(statementCode: string): string {
  return statementCode.trim().replace(/\s+/g, ' ').toUpperCase();
}

// Adds per-request timeout and maps network/timeout errors to domain types.
async function kgFetchFn(input: Request, init?: Parameters<typeof fetch>[1]): Promise<Response> {
  try {
    return await fetch(input, { ...init, signal: AbortSignal.timeout(KG_TIMEOUT_MS) });
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      throw new NetworkError(`Knowledge Graph request timed out after ${KG_TIMEOUT_MS}ms`);
    }
    throw new NetworkError(`Knowledge Graph request failed: ${err instanceof Error ? err.message : String(err)}`);
  }
}

function wrapJsonError(err: unknown): never {
  if (err instanceof SyntaxError) {
    throw new KnowledgeGraphError(`Knowledge Graph returned invalid JSON: ${err.message}`);
  }
  throw err;
}

// Maps HTTP error responses to domain error types.
const httpErrorMiddleware: Middleware = {
  async onResponse({ response }) {
    if (!response.ok) {
      const body = await response.text().catch(() => '');
      if (response.status === 401 || response.status === 403) {
        throw new AuthenticationError(`Knowledge Graph authentication failed: ${body}`, response.status);
      }
      if (response.status === 429) {
        throw new RateLimitError(`Knowledge Graph rate limit exceeded: ${body}`);
      }
      throw new KnowledgeGraphError(`Knowledge Graph request failed (${response.status}): ${body}`, response.status);
    }
  },
};

export interface StandardInfoOptions {
  jurisdiction?: string;
  academicSubject?: string;
}

export interface StandardsByGradeOptions {
  jurisdiction?: string;
  academicSubject?: string;
}

/**
 * HTTP client for the Learning Commons Knowledge Graph API.
 *
 * Handles standard and learning component lookups with concurrency limiting
 * and promise caching. Rejected promises are evicted so transient errors
 * (429, network blips) are retryable on the next call.
 */
export class KnowledgeGraphClient {
  private readonly limit: ReturnType<typeof pLimit>;
  private readonly http: ReturnType<typeof createClient<paths>>;

  // Cache key: `${normalizedCode}:${jurisdiction}:${academicSubject}`
  // Holds every candidate, so resolving an ambiguous code costs no extra request.
  private readonly standardInfoCache = new Map<string, Promise<StandardInfo[]>>();
  private readonly lcCache = new Map<string, Promise<LearningComponentSet>>();
  // Cache key: `${jurisdiction}:${academicSubject}`
  private readonly frameworkUuidCache = new Map<string, Promise<string>>();

  constructor(apiKey: string, concurrency = 20) {
    this.limit = pLimit(concurrency);
    this.http = createClient<paths>({
      baseUrl: KG_BASE_URL,
      headers: { 'x-api-key': apiKey },
      fetch: kgFetchFn,
    });
    this.http.use(httpErrorMiddleware);
  }

  /** The first matching standard. Sets `ambiguous` when the code matched more than one. */
  async getStandardInfo(statementCode: string, opts?: StandardInfoOptions): Promise<StandardInfo> {
    const candidates = await this.getStandardCandidates(statementCode, opts);
    return { ...candidates[0], ...(candidates.length > 1 ? { ambiguous: true } : {}) };
  }

  /**
   * Every standard matching the code, in Knowledge Graph order. More than one means
   * the code is reused (typically across courses) and the caller must choose. A
   * length of {@link STANDARD_SEARCH_LIMIT} may be truncated — search takes no cursor.
   */
  async getStandardCandidates(statementCode: string, opts?: StandardInfoOptions): Promise<StandardInfo[]> {
    const normalized = normalizeStatementCode(statementCode);
    const jurisdiction = opts?.jurisdiction ?? 'Multi-State';
    const cacheKey = `${normalized}:${jurisdiction}:${opts?.academicSubject ?? ''}`;
    let p = this.standardInfoCache.get(cacheKey);
    if (!p) {
      p = this.limit(() => this._fetchStandardCandidates(normalized, opts));
      p = p.catch((err) => { this.standardInfoCache.delete(cacheKey); throw err; });
      this.standardInfoCache.set(cacheKey, p);
    }

    const candidates = await p;
    if (candidates.length === 0) {
      // Evict: an empty result fulfils rather than rejects, so the eviction above
      // never fires and a transient empty response would be cached for the life of
      // the client. Guarded on identity so a concurrent retry is not discarded.
      if (this.standardInfoCache.get(cacheKey) === p) this.standardInfoCache.delete(cacheKey);
      // Thrown per caller, not inside the shared request, so concurrent callers with
      // different spellings each see their own in the message.
      throw new KnowledgeGraphError(`Standard not found: "${statementCode}"`);
    }
    // Copies: a caller sorting these to choose would otherwise reorder the cache.
    return candidates.map((c) => ({ ...c }));
  }

  /** Evaluable components only. See {@link getLearningComponentSet} to tell an
   * empty standard apart from one whose components have no descriptions. */
  async getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    return (await this.getLearningComponentSet(caseIdentifierUUID)).components;
  }

  getLearningComponentSet(caseIdentifierUUID: string): Promise<LearningComponentSet> {
    let p = this.lcCache.get(caseIdentifierUUID);
    if (!p) {
      p = this.limit(() => this._fetchLearningComponents(caseIdentifierUUID));
      p = p.catch((err) => { this.lcCache.delete(caseIdentifierUUID); throw err; });
      this.lcCache.set(caseIdentifierUUID, p);
    }
    return p;
  }

  async getStandardsByGrade(grade: string, opts?: StandardsByGradeOptions): Promise<AcademicStandard[]> {
    const frameworkUuid = await this._getFrameworkUuid(
      opts?.jurisdiction ?? 'Multi-State',
      opts?.academicSubject,
    );

    type StandardsQuery = NonNullable<
      paths['/academic-standards']['get']['parameters']['query']
    >;

    return this._paginate(`grade "${grade}"`, async (cursor) => {
      const query: StandardsQuery = {
        limit: STANDARDS_PAGE_SIZE,
        standardsFrameworkCaseIdentifierUUID: frameworkUuid,
        gradeLevel: [grade] as components['parameters']['GradeLevelParam'],
        normalizedStatementType: 'Standard' as components['schemas']['NormalizedStatementTypeENUM'],
        ...(opts?.academicSubject
          ? { academicSubject: opts.academicSubject as components['schemas']['AcademicSubjectENUM'] }
          : {}),
        ...(cursor ? { cursor } : {}),
      };

      const { data } = await this.http.GET('/academic-standards', {
        params: { query },
      }).catch(wrapJsonError);
      if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

      return {
        items: (data.data ?? []).map((item) => ({
          caseIdentifierUUID: item.caseIdentifierUUID,
          statementCode: item.statementCode ?? null,
          description: item.description ?? null,
          statementType: item.statementType ?? null,
          normalizedStatementType: item.normalizedStatementType ?? null,
          gradeLevel: item.gradeLevel ?? [],
        })),
        hasMore: data.pagination?.hasMore,
        nextCursor: data.pagination?.nextCursor,
      };
    });
  }

  async getLearningComponentsByCode(
    statementCode: string,
    opts?: StandardInfoOptions,
  ): Promise<StandardInfo & { components: LearningComponent[] }> {
    const info = await this.getStandardInfo(statementCode, opts);
    const components = await this.getLearningComponents(info.uuid);
    return { ...info, components };
  }

  // ---------------------------------------------------------------------------

  /**
   * Walks cursor-paginated KG endpoints until exhausted. `context` labels the
   * error thrown when a page's pagination fields are self-contradictory, which
   * would otherwise loop forever or truncate silently.
   */
  private async _paginate<T>(
    context: string,
    fetchPage: (cursor: string | null) => Promise<{
      items: T[];
      hasMore?: boolean;
      nextCursor?: string | null;
    }>,
  ): Promise<T[]> {
    const results: T[] = [];
    const seenCursors = new Set<string>();
    let cursor: string | null = null;

    do {
      const { items, hasMore, nextCursor } = await fetchPage(cursor);
      results.push(...items);

      if (hasMore && !nextCursor) {
        throw new KnowledgeGraphError(
          `Knowledge Graph pagination error: hasMore=true but nextCursor is null for ${context}`,
        );
      }
      cursor = hasMore ? (nextCursor ?? null) : null;

      if (cursor !== null) {
        if (seenCursors.has(cursor)) {
          throw new KnowledgeGraphError(
            `Knowledge Graph pagination error: cursor "${cursor}" repeated for ${context}`,
          );
        }
        seenCursors.add(cursor);
        // The repeat check above misses a server minting a fresh cursor per page.
        if (seenCursors.size > MAX_PAGES) {
          throw new KnowledgeGraphError(
            `Knowledge Graph pagination error: exceeded ${MAX_PAGES} pages for ${context}`,
          );
        }
      }
    } while (cursor !== null);

    return results;
  }

  private _getFrameworkUuid(jurisdiction: string, academicSubject?: string): Promise<string> {
    if (jurisdiction === 'Multi-State') return Promise.resolve(CCSS_FRAMEWORK_UUID);

    const cacheKey = `${jurisdiction}:${academicSubject ?? ''}`;
    let p = this.frameworkUuidCache.get(cacheKey);
    if (!p) {
      p = this.limit(() => this._fetchFrameworkUuid(jurisdiction, academicSubject));
      p = p.catch((err) => { this.frameworkUuidCache.delete(cacheKey); throw err; });
      this.frameworkUuidCache.set(cacheKey, p);
    }
    return p;
  }

  private async _fetchFrameworkUuid(jurisdiction: string, academicSubject?: string): Promise<string> {
    const { data } = await this.http.GET('/standards-frameworks', {
      params: {
        query: {
          jurisdiction: jurisdiction as components['schemas']['JurisdictionENUM'],
          limit: 1,
          ...(academicSubject
            ? { academicSubject: academicSubject as components['schemas']['AcademicSubjectENUM'] }
            : {}),
        },
      },
    }).catch(wrapJsonError);
    if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

    const frameworks = data.data ?? [];
    if (frameworks.length === 0) {
      throw new KnowledgeGraphError(
        `No standards framework found for jurisdiction "${jurisdiction}"` +
        (academicSubject ? ` and subject "${academicSubject}"` : ''),
      );
    }
    return frameworks[0].caseIdentifierUUID;
  }

  /** Empty when the code does not exist; the caller raises the not-found error. */
  private async _fetchStandardCandidates(
    normalizedCode: string,
    opts?: StandardInfoOptions,
  ): Promise<StandardInfo[]> {
    const { data } = await this.http.GET('/academic-standards/search', {
      params: {
        query: {
          statementCode: normalizedCode,
          jurisdiction: (opts?.jurisdiction ?? 'Multi-State') as components['schemas']['JurisdictionENUM'],
          limit: STANDARD_SEARCH_LIMIT,
          ...(opts?.academicSubject
            ? { academicSubject: opts.academicSubject as components['schemas']['AcademicSubjectENUM'] }
            : {}),
        },
      },
    }).catch(wrapJsonError);
    if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

    return data.map((item) => ({
      uuid: item.caseIdentifierUUID,
      description: item.description ?? undefined,
      // The KG's spelling: CCSS sub-standards are lowercase (3.MD.C.7.d), so the
      // uppercased lookup key is not a valid code. Fallback is defensive only.
      statementCode: item.statementCode ?? normalizedCode,
      normalizedCode,
    }));
  }

  private async _fetchLearningComponents(caseIdentifierUUID: string): Promise<LearningComponentSet> {
    let undescribedCount = 0;
    const components = await this._paginate(`UUID ${caseIdentifierUUID}`, async (cursor) => {
      const query: { limit: number; cursor?: string } = { limit: LC_PAGE_SIZE };
      if (cursor) query.cursor = cursor;

      const { data } = await this.http.GET('/academic-standards/{caseIdentifierUUID}/learning-components', {
        params: { path: { caseIdentifierUUID }, query },
      }).catch(wrapJsonError);
      if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

      const items: LearningComponent[] = [];
      for (const item of data.data ?? []) {
        if (item.description != null) {
          items.push({ identifier: item.identifier, description: item.description });
        } else {
          undescribedCount++;
        }
      }

      return { items, hasMore: data.pagination?.hasMore, nextCursor: data.pagination?.nextCursor };
    });

    return { components, undescribedCount };
  }
}
