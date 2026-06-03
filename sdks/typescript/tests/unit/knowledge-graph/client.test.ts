import { describe, it, expect, vi } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import type { StandardsRepository, StandardInfo } from '../../../src/knowledge-graph/types.js';

const MOCK_INFO: StandardInfo = { uuid: 'test-uuid', description: 'Area additive' };

function makeRepo(overrides: Partial<StandardsRepository> = {}): StandardsRepository {
  return {
    getStandardInfo: vi.fn().mockResolvedValue(MOCK_INFO),
    getLearningComponents: vi.fn().mockResolvedValue([{ description: 'LC one' }]),
    getStandardsByGrade: vi.fn().mockResolvedValue([]),
    ...overrides,
  };
}

describe('KnowledgeGraphClient - getLearningComponentsByCode', () => {
  it('chains getStandardInfo then getLearningComponents using the uuid from StandardInfo', async () => {
    const repo = makeRepo();
    const client = new KnowledgeGraphClient(repo);
    const result = await client.getLearningComponentsByCode('3.MD.C.7.d');

    expect(repo.getStandardInfo).toHaveBeenCalledWith('3.MD.C.7.d');
    expect(repo.getLearningComponents).toHaveBeenCalledWith('test-uuid');
    expect(result.uuid).toBe('test-uuid');
    expect(result.description).toBe('Area additive');
    expect(result.components).toHaveLength(1);
    expect(result.components[0].description).toBe('LC one');
  });

  it('propagates errors from getStandardInfo', async () => {
    const repo = makeRepo({
      getStandardInfo: vi.fn().mockRejectedValue(new Error('not found')),
    });
    const client = new KnowledgeGraphClient(repo);
    await expect(client.getLearningComponentsByCode('bad')).rejects.toThrow('not found');
  });

  it('evicts standard info cache on rejection so a retry can succeed', async () => {
    const getStandardInfo = vi.fn()
      .mockRejectedValueOnce(new Error('transient 429'))
      .mockResolvedValue({ uuid: 'recovered-uuid', description: 'Recovered' });
    const repo = makeRepo({ getStandardInfo });
    const client = new KnowledgeGraphClient(repo);

    await expect(client.getStandardInfo('3.MD.C.7.d')).rejects.toThrow('transient 429');
    const info = await client.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('recovered-uuid');
    expect(getStandardInfo).toHaveBeenCalledTimes(2);
  });

  it('propagates errors from getLearningComponents', async () => {
    const repo = makeRepo({
      getLearningComponents: vi.fn().mockRejectedValue(new Error('server error')),
    });
    const client = new KnowledgeGraphClient(repo);
    await expect(client.getLearningComponentsByCode('3.MD.C.7.d')).rejects.toThrow('server error');
  });

  it('evicts LC cache on rejection so a retry can succeed', async () => {
    const getLearningComponents = vi.fn()
      .mockRejectedValueOnce(new Error('transient 503'))
      .mockResolvedValue([{ description: 'Recovered LC' }]);
    const repo = makeRepo({ getLearningComponents });
    const client = new KnowledgeGraphClient(repo);

    await expect(client.getLearningComponents('uuid-abc')).rejects.toThrow('transient 503');
    const lcs = await client.getLearningComponents('uuid-abc');
    expect(lcs[0].description).toBe('Recovered LC');
    expect(getLearningComponents).toHaveBeenCalledTimes(2);
  });
});

describe('KnowledgeGraphClient - getStandardsByGrade', () => {
  it('delegates directly to repository', async () => {
    const repo = makeRepo({
      getStandardsByGrade: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: '3.OA.A.1', description: 'test', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const client = new KnowledgeGraphClient(repo);
    const results = await client.getStandardsByGrade('3', { excludeMP: true });
    expect(repo.getStandardsByGrade).toHaveBeenCalledWith('3', { excludeMP: true });
    expect(results).toHaveLength(1);
  });
});
