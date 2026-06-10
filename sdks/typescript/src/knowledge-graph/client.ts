import pLimit from 'p-limit';
import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
} from '../errors.js';
import type { AcademicStandard, LearningComponent, StandardInfo } from './types.js';
import type { components } from './kg-api.js';

const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';
const KG_TIMEOUT_MS = 30_000;

type SpecLearningComponent = components['schemas']['LearningComponent'];

async function kgFetch(url: string, apiKey: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, {
      headers: { 'x-api-key': apiKey },
      signal: AbortSignal.timeout(KG_TIMEOUT_MS),
    });
  } catch (err) {
    if (err instanceof Error && err.name === 'TimeoutError') {
      throw new NetworkError(`Knowledge Graph request timed out after ${KG_TIMEOUT_MS}ms`);
    }
    throw new NetworkError(`Knowledge Graph request failed: ${err instanceof Error ? err.message : String(err)}`);
  }

  if (response.ok) {
    return response.json().catch((err: unknown) => {
      throw new KnowledgeGraphError(
        `Knowledge Graph returned invalid JSON: ${err instanceof Error ? err.message : String(err)}`,
      );
    });
  }

  const body = await response.text().catch(() => '');

  if (response.status === 401 || response.status === 403) {
    throw new AuthenticationError(`Knowledge Graph authentication failed: ${body}`, response.status);
  }
  if (response.status === 429) {
    throw new RateLimitError(`Knowledge Graph rate limit exceeded: ${body}`);
  }
  throw new KnowledgeGraphError(
    `Knowledge Graph request failed (${response.status}): ${body}`,
    response.status,
  );
}

/**
 * HTTP client for the Learning Commons Knowledge Graph API.
 *
 * Handles standard and learning component lookups with concurrency limiting
 * and promise caching. Rejected promises are evicted so transient errors
 * (429, network blips) are retryable on the next call.
 */
export class KnowledgeGraphClient {
  private readonly apiKey: string;
  private readonly limit: ReturnType<typeof pLimit>;

  private readonly standardInfoCache = new Map<string, Promise<StandardInfo>>();
  private readonly lcCache = new Map<string, Promise<LearningComponent[]>>();

  constructor(apiKey: string, concurrency = 20) {
    this.apiKey = apiKey;
    this.limit = pLimit(concurrency);
  }

  getStandardInfo(statementCode: string): Promise<StandardInfo> {
    let p = this.standardInfoCache.get(statementCode);
    if (!p) {
      p = this.limit(() => this._fetchStandardInfo(statementCode));
      p = p.catch((err) => { this.standardInfoCache.delete(statementCode); throw err; });
      this.standardInfoCache.set(statementCode, p);
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

  async getStandardsByGrade(grade: string): Promise<AcademicStandard[]> {
    const url =
      `${KG_BASE_URL}/academic-standards?limit=500` +
      `&standardsFrameworkCaseIdentifierUUID=${CCSS_FRAMEWORK_UUID}` +
      `&academicSubject=Mathematics` +
      `&gradeLevel=${encodeURIComponent(grade)}` +
      `&normalizedStatementType=Standard`;

    const data = (await kgFetch(url, this.apiKey)) as {
      data: Array<AcademicStandard>;
      pagination?: { hasMore: boolean; nextCursor: string | null };
    };

    if (data.pagination?.hasMore) {
      throw new KnowledgeGraphError(
        `getStandardsByGrade returned a paginated result for grade "${grade}" — ` +
        `increase limit or implement cursor pagination to retrieve all standards.`,
      );
    }

    return (data.data ?? []).map((item) => ({
        caseIdentifierUUID: item.caseIdentifierUUID,
        statementCode: item.statementCode,
        description: item.description,
        statementType: item.statementType,
        normalizedStatementType: item.normalizedStatementType,
        gradeLevel: item.gradeLevel ?? [],
      }));
  }

  async getLearningComponentsByCode(
    statementCode: string,
  ): Promise<{ uuid: string; description?: string; components: LearningComponent[] }> {
    const { uuid, description } = await this.getStandardInfo(statementCode);
    const components = await this.getLearningComponents(uuid);
    return { uuid, description, components };
  }

  // ---------------------------------------------------------------------------

  private async _fetchStandardInfo(statementCode: string): Promise<StandardInfo> {
    const url = `${KG_BASE_URL}/academic-standards/search?jurisdiction=Multi-State&statementCode=${encodeURIComponent(statementCode)}`;
    const data = (await kgFetch(url, this.apiKey)) as Array<{ caseIdentifierUUID: string; description?: string }>;

    if (!Array.isArray(data) || data.length === 0) {
      throw new KnowledgeGraphError(`Standard not found: "${statementCode}"`);
    }
    if (data.length > 1) {
      throw new KnowledgeGraphError(`Ambiguous standard code: "${statementCode}", ${data.length} results returned`);
    }
    return { uuid: data[0].caseIdentifierUUID, description: data[0].description };
  }

  private async _fetchLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    const results: LearningComponent[] = [];
    let cursor: string | null = null;

    do {
      const url =
        `${KG_BASE_URL}/academic-standards/${encodeURIComponent(caseIdentifierUUID)}/learning-components?limit=100` +
        (cursor ? `&cursor=${encodeURIComponent(cursor)}` : '');

      const page = (await kgFetch(url, this.apiKey)) as {
        data: SpecLearningComponent[];
        pagination: { hasMore: boolean; nextCursor: string | null };
      };

      for (const item of page.data ?? []) {
        if (item.description != null) {
          results.push({ description: item.description });
        }
      }

      const { hasMore, nextCursor } = page.pagination ?? {};
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
