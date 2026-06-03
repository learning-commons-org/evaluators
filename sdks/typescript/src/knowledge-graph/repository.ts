import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
} from '../errors.js';
import type { AcademicStandard, LearningComponent, LearningComponentRaw, GetStandardsOptions, StandardInfo, StandardsRepository } from './types.js';

const KG_BASE_URL = 'https://api.learningcommons.org/knowledge-graph/v0';
const CCSS_FRAMEWORK_UUID = 'c6496676-d7cb-11e8-824f-0242ac160002';

async function kgFetch(url: string, apiKey: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(url, { headers: { 'x-api-key': apiKey } });
  } catch (err) {
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
        data: LearningComponentRaw[];
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

  async getStandardsByGrade(grade: string, options?: GetStandardsOptions): Promise<AcademicStandard[]> {
    const excludeMP = options?.excludeMP !== false;
    const url =
      `${KG_BASE_URL}/academic-standards?limit=500` +
      `&standardsFrameworkCaseIdentifierUUID=${CCSS_FRAMEWORK_UUID}` +
      `&academicSubject=Mathematics` +
      `&gradeLevel=${encodeURIComponent(grade)}` +
      `&normalizedStatementType=Standard`;

    const data = (await kgFetch(url, this.apiKey)) as {
      data: Array<{
        caseIdentifierUUID: string;
        statementCode: string;
        description: string;
        statementType: string;
        normalizedStatementType: string;
        gradeLevel: string[];
      }>;
    };

    const standards: AcademicStandard[] = (data.data ?? []).map((item) => ({
      caseIdentifierUUID: item.caseIdentifierUUID,
      statementCode: item.statementCode,
      description: item.description,
      statementType: item.statementType,
      normalizedStatementType: item.normalizedStatementType,
      gradeLevel: item.gradeLevel ?? [],
    }));

    return excludeMP ? standards.filter((s) => !s.statementCode.includes('MP')) : standards;
  }
}

// ---------------------------------------------------------------------------
// JSON export repository — for offline / static data usage
// ---------------------------------------------------------------------------

interface KgJsonStandard {
  caseIdentifierUUID: string;
  statementCode: string;
  description: string;
  statementType: string;
  normalizedStatementType: string;
  gradeLevel?: string | string[];
  learningComponents?: Array<{ description: string | null }>;
}

export class KnowledgeGraphJsonRepository implements StandardsRepository {
  private readonly standards: KgJsonStandard[];

  constructor(data: { standards: KgJsonStandard[] }) {
    this.standards = data.standards;
  }

  async getStandardInfo(statementCode: string): Promise<StandardInfo> {
    const matches = this.standards.filter((s) => s.statementCode === statementCode);
    if (matches.length === 0) throw new KnowledgeGraphError(`Standard not found: "${statementCode}"`);
    if (matches.length > 1) throw new KnowledgeGraphError(`Ambiguous standard code: "${statementCode}", ${matches.length} results`);
    return { uuid: matches[0].caseIdentifierUUID, description: matches[0].description };
  }

  async getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    const standard = this.standards.find((s) => s.caseIdentifierUUID === caseIdentifierUUID);
    return (standard?.learningComponents ?? [])
      .filter((lc) => lc.description != null)
      .map((lc) => ({ description: lc.description as string }));
  }

  async getStandardsByGrade(grade: string, options?: GetStandardsOptions): Promise<AcademicStandard[]> {
    const excludeMP = options?.excludeMP !== false;
    const results = this.standards
      .filter((s) => {
        const gl = s.gradeLevel;
        const matches = Array.isArray(gl) ? gl.includes(grade) : gl === grade;
        return matches && s.normalizedStatementType === 'Standard';
      })
      .map((s) => ({
        caseIdentifierUUID: s.caseIdentifierUUID,
        statementCode: s.statementCode,
        description: s.description,
        statementType: s.statementType,
        normalizedStatementType: s.normalizedStatementType,
        gradeLevel: Array.isArray(s.gradeLevel) ? s.gradeLevel : s.gradeLevel ? [s.gradeLevel] : [],
      }));
    return excludeMP ? results.filter((s) => !s.statementCode.includes('MP')) : results;
  }
}
