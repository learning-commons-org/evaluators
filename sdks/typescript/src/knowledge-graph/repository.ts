import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
} from '../errors.js';
import type { AcademicStandard, LearningComponent, StandardInfo, StandardsRepository } from './types.js';
import type { components } from './kg-api.js';

// Use the spec type for the raw LC response before description-null filtering
type SpecLearningComponent = components['schemas']['LearningComponent'];

const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';

const KG_TIMEOUT_MS = 30_000;

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

export class KnowledgeGraphApiRepository implements StandardsRepository {
  constructor(private readonly apiKey: string) {}

  async getStandardInfo(statementCode: string): Promise<StandardInfo> {
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

  async getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    const results: LearningComponent[] = [];
    let cursor: string | null = null;

    // Follow cursor-based pagination until no more pages
    do {
      const url =
        `${KG_BASE_URL}/academic-standards/${encodeURIComponent(caseIdentifierUUID)}/learning-components?limit=100` +
        (cursor ? `&cursor=${encodeURIComponent(cursor)}` : '');

      const page = (await kgFetch(url, this.apiKey)) as {
        data: SpecLearningComponent[];
        pagination: { hasMore: boolean; nextCursor: string | null };
      };

      // description is nullable per the API spec — skip nulls
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

  async getStandardsByGrade(grade: string): Promise<AcademicStandard[]> {
    // Mathematical Practice standards are excluded by constraining to
    // normalizedStatementType=Standard — matching the original Python notebook behaviour.
    const url =
      `${KG_BASE_URL}/academic-standards?limit=500` +
      `&standardsFrameworkCaseIdentifierUUID=${CCSS_FRAMEWORK_UUID}` +
      `&academicSubject=Mathematics` +
      `&gradeLevel=${encodeURIComponent(grade)}` +
      `&normalizedStatementType=Standard`;

    const data = (await kgFetch(url, this.apiKey)) as {
      data: Array<AcademicStandard>;
    };

    return (data.data ?? [])
      .filter((item) => item.normalizedStatementType !== 'Mathematical Practice')
      .map((item) => ({
        caseIdentifierUUID: item.caseIdentifierUUID,
        statementCode: item.statementCode,
        description: item.description,
        statementType: item.statementType,
        normalizedStatementType: item.normalizedStatementType,
        gradeLevel: item.gradeLevel ?? [],
      }));
  }
}

