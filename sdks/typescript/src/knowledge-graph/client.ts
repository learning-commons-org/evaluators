import pLimit from 'p-limit';
import createClient, { type Middleware } from 'openapi-fetch';
import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
} from '../errors.js';
import type { AcademicStandard, LearningComponent, StandardInfo } from './types.js';
import type { paths, components } from './kg-api.js';

const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';
const KG_TIMEOUT_MS = 30_000;

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
  limit?: number;
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

  // Cache key: `${statementCode}:${jurisdiction}`
  private readonly standardInfoCache = new Map<string, Promise<StandardInfo>>();
  private readonly lcCache = new Map<string, Promise<LearningComponent[]>>();
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

  getStandardInfo(statementCode: string, opts?: StandardInfoOptions): Promise<StandardInfo> {
    const jurisdiction = opts?.jurisdiction ?? 'Multi-State';
    const cacheKey = `${statementCode}:${jurisdiction}`;
    let p = this.standardInfoCache.get(cacheKey);
    if (!p) {
      p = this.limit(() => this._fetchStandardInfo(statementCode, opts));
      p = p.catch((err) => { this.standardInfoCache.delete(cacheKey); throw err; });
      this.standardInfoCache.set(cacheKey, p);
    }
    return p;
  }

  getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
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

    const { data } = await this.http.GET('/academic-standards', {
      params: {
        query: {
          limit: 500,
          standardsFrameworkCaseIdentifierUUID: frameworkUuid,
          gradeLevel: [grade] as components['parameters']['GradeLevelParam'],
          normalizedStatementType: 'Standard' as components['schemas']['NormalizedStatementTypeENUM'],
          ...(opts?.academicSubject
            ? { academicSubject: opts.academicSubject as components['schemas']['AcademicSubjectENUM'] }
            : {}),
        },
      },
    }).catch(wrapJsonError);
    if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

    if (data.pagination?.hasMore) {
      throw new KnowledgeGraphError(
        `getStandardsByGrade returned a paginated result for grade "${grade}" — ` +
        `increase limit or implement cursor pagination to retrieve all standards.`,
      );
    }

    return (data.data ?? []).map((item) => ({
      caseIdentifierUUID: item.caseIdentifierUUID,
      statementCode: item.statementCode ?? null,
      description: item.description ?? null,
      statementType: item.statementType ?? null,
      normalizedStatementType: item.normalizedStatementType ?? null,
      gradeLevel: item.gradeLevel ?? [],
    }));
  }

  async getLearningComponentsByCode(
    statementCode: string,
    opts?: StandardInfoOptions,
  ): Promise<{ uuid: string; description?: string; components: LearningComponent[] }> {
    const { uuid, description } = await this.getStandardInfo(statementCode, opts);
    const components = await this.getLearningComponents(uuid);
    return { uuid, description, components };
  }

  // ---------------------------------------------------------------------------

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

  private async _fetchStandardInfo(statementCode: string, opts?: StandardInfoOptions): Promise<StandardInfo> {
    const { data } = await this.http.GET('/academic-standards/search', {
      params: {
        query: {
          statementCode,
          jurisdiction: (opts?.jurisdiction ?? 'Multi-State') as components['schemas']['JurisdictionENUM'],
          limit: opts?.limit ?? 1,
          ...(opts?.academicSubject
            ? { academicSubject: opts.academicSubject as components['schemas']['AcademicSubjectENUM'] }
            : {}),
        },
      },
    }).catch(wrapJsonError);
    if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

    if (data.length === 0) {
      throw new KnowledgeGraphError(`Standard not found: "${statementCode}"`);
    }
    return { uuid: data[0].caseIdentifierUUID, description: data[0].description ?? undefined };
  }

  private async _fetchLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    const results: LearningComponent[] = [];
    let cursor: string | null = null;

    do {
      const query: { limit: number; cursor?: string } = { limit: 100 };
      if (cursor) query.cursor = cursor;

      const { data } = await this.http.GET('/academic-standards/{caseIdentifierUUID}/learning-components', {
        params: { path: { caseIdentifierUUID }, query },
      }).catch(wrapJsonError);
      if (data === undefined) throw new KnowledgeGraphError('Unexpected empty response from Knowledge Graph');

      for (const item of data.data ?? []) {
        if (item.description != null) {
          results.push({ identifier: item.identifier, description: item.description });
        }
      }

      const { hasMore, nextCursor } = data.pagination ?? {};
      if (hasMore && !nextCursor) {
        throw new KnowledgeGraphError(
          `Knowledge Graph pagination error: hasMore=true but nextCursor is null for UUID ${caseIdentifierUUID}`,
        );
      }
      cursor = hasMore ? (nextCursor ?? null) : null;
    } while (cursor !== null);

    return results;
  }
}
