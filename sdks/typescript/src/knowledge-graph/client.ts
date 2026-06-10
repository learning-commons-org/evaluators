import pLimit from 'p-limit';
import type { AcademicStandard, LearningComponent, StandardInfo, StandardsRepository } from './types.js';

export class KnowledgeGraphClient {
  private readonly repository: StandardsRepository;
  private readonly limit: ReturnType<typeof pLimit>;

  // Promise caches keyed by statementCode / UUID.
  // Concurrent callers for the same key share the same in-flight promise (no duplicate requests).
  // Rejected promises are evicted so transient errors (429, network blip) can be retried on
  // the next call — only successful results are kept.
  private readonly standardInfoCache = new Map<string, Promise<StandardInfo>>();
  private readonly lcCache = new Map<string, Promise<LearningComponent[]>>();

  constructor(repository: StandardsRepository, concurrency = 20) {
    this.repository = repository;
    this.limit = pLimit(concurrency);
  }

  getStandardInfo(statementCode: string): Promise<StandardInfo> {
    let p = this.standardInfoCache.get(statementCode);
    if (!p) {
      p = this.limit(() => this.repository.getStandardInfo(statementCode));
      p = p.catch((err) => {
        this.standardInfoCache.delete(statementCode);
        throw err;
      });
      this.standardInfoCache.set(statementCode, p);
    }
    return p;
  }

  getLearningComponents(caseIdentifierUUID: string): Promise<LearningComponent[]> {
    let p = this.lcCache.get(caseIdentifierUUID);
    if (!p) {
      p = this.limit(() => this.repository.getLearningComponents(caseIdentifierUUID));
      p = p.catch((err) => {
        this.lcCache.delete(caseIdentifierUUID);
        throw err;
      });
      this.lcCache.set(caseIdentifierUUID, p);
    }
    return p;
  }

  getStandardsByGrade(grade: string): Promise<AcademicStandard[]> {
    return this.repository.getStandardsByGrade(grade);
  }

  async getLearningComponentsByCode(
    statementCode: string,
  ): Promise<{ uuid: string; description?: string; components: LearningComponent[] }> {
    const { uuid, description } = await this.getStandardInfo(statementCode);
    const components = await this.getLearningComponents(uuid);
    return { uuid, description, components };
  }
}
