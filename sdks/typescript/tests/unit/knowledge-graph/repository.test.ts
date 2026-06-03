import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphApiRepository, KnowledgeGraphJsonRepository } from '../../../src/knowledge-graph/repository.js';
import { KnowledgeGraphError, AuthenticationError, RateLimitError, NetworkError } from '../../../src/errors.js';

// ---------------------------------------------------------------------------
// KnowledgeGraphApiRepository
// ---------------------------------------------------------------------------

const API_KEY = 'test-key';

function mockFetch(status: number, body: unknown) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(text),
  }));
}

describe('KnowledgeGraphApiRepository - getStandardInfo', () => {
  beforeEach(() => { vi.unstubAllGlobals(); });

  it('returns uuid and description when exactly one standard found', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'abc-123', description: 'Recognize area as additive' }]);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const info = await repo.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('abc-123');
    expect(info.description).toBe('Recognize area as additive');
  });

  it('returns uuid with no description when description is absent', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'abc-123' }]);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const info = await repo.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('abc-123');
    expect(info.description).toBeUndefined();
  });

  it('throws KnowledgeGraphError when no standard found', async () => {
    mockFetch(200, []);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('X.YZ.A.1')).rejects.toThrow(KnowledgeGraphError);
    await expect(repo.getStandardInfo('X.YZ.A.1')).rejects.toThrow('not found');
  });

  it('throws KnowledgeGraphError when ambiguous (>1 results)', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'a' }, { caseIdentifierUUID: 'b' }]);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('3.MD')).rejects.toThrow(KnowledgeGraphError);
    await expect(repo.getStandardInfo('3.MD')).rejects.toThrow('Ambiguous');
  });

  it('throws AuthenticationError on 401', async () => {
    mockFetch(401, 'Unauthorized');
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('3.MD.C.7.d')).rejects.toThrow(AuthenticationError);
  });

  it('throws AuthenticationError on 403', async () => {
    mockFetch(403, 'Forbidden');
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('3.MD.C.7.d')).rejects.toThrow(AuthenticationError);
  });

  it('throws RateLimitError on 429', async () => {
    mockFetch(429, 'Too Many Requests');
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('3.MD.C.7.d')).rejects.toThrow(RateLimitError);
  });

  it('throws KnowledgeGraphError with statusCode on 500', async () => {
    mockFetch(500, 'Server Error');
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const err = await repo.getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.statusCode).toBe(500);
  });

  it('throws NetworkError when fetch throws', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getStandardInfo('3.MD.C.7.d')).rejects.toThrow(NetworkError);
  });
});

describe('KnowledgeGraphApiRepository - getLearningComponents', () => {
  beforeEach(() => { vi.unstubAllGlobals(); });

  it('returns learning components from data array', async () => {
    mockFetch(200, {
      data: [
        { identifier: 'lc-1', description: 'Recognize area as additive' },
        { identifier: 'lc-2', description: 'Find areas of rectilinear figures' },
      ],
      pagination: { hasMore: false, nextCursor: null },
    });
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const lcs = await repo.getLearningComponents('abc-123');
    expect(lcs).toHaveLength(2);
    expect(lcs[0].description).toBe('Recognize area as additive');
    expect(lcs[1].description).toBe('Find areas of rectilinear figures');
  });

  it('filters out null descriptions', async () => {
    mockFetch(200, {
      data: [
        { identifier: 'lc-1', description: 'Valid LC' },
        { identifier: 'lc-2', description: null },
        { identifier: 'lc-3', description: 'Another valid LC' },
      ],
      pagination: { hasMore: false, nextCursor: null },
    });
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const lcs = await repo.getLearningComponents('abc-123');
    expect(lcs).toHaveLength(2);
    expect(lcs.map((lc) => lc.description)).toEqual(['Valid LC', 'Another valid LC']);
  });

  it('follows cursor pagination to fetch all pages', async () => {
    let callCount = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => {
      callCount++;
      const isFirstPage = callCount === 1;
      return Promise.resolve({
        ok: true, status: 200,
        json: () => Promise.resolve({
          data: [{ identifier: `lc-${callCount}`, description: `LC ${callCount}` }],
          pagination: { hasMore: isFirstPage, nextCursor: isFirstPage ? 'cursor-page-2' : null },
        }),
        text: () => Promise.resolve(''),
      });
    }));

    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const lcs = await repo.getLearningComponents('abc-123');
    expect(lcs).toHaveLength(2);
    expect(callCount).toBe(2);
  });

  it('returns empty array when data is empty', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: false, nextCursor: null } });
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    expect(await repo.getLearningComponents('abc-123')).toHaveLength(0);
  });

  it('throws KnowledgeGraphError on non-2xx', async () => {
    mockFetch(404, 'Not Found');
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    await expect(repo.getLearningComponents('bad-uuid')).rejects.toThrow(KnowledgeGraphError);
  });
});

describe('KnowledgeGraphApiRepository - getStandardsByGrade', () => {
  beforeEach(() => { vi.unstubAllGlobals(); });

  const gradeData = {
    data: [
      { caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', description: 'Area additive', statementType: 'Standard', normalizedStatementType: 'Standard' },
      { caseIdentifierUUID: 'u2', statementCode: '3.MP.1', description: 'Make sense of problems', statementType: 'Mathematical Practice', normalizedStatementType: 'Mathematical Practice' },
      { caseIdentifierUUID: 'u3', statementCode: '3.OA.A.1', description: 'Interpret products', statementType: 'Standard', normalizedStatementType: 'Standard' },
    ],
  };

  it('excludes MP standards by default', async () => {
    mockFetch(200, gradeData);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const results = await repo.getStandardsByGrade('3');
    const codes = results.map((s) => s.statementCode);
    expect(codes).not.toContain('3.MP.1');
    expect(codes).toContain('3.MD.C.7.d');
    expect(codes).toContain('3.OA.A.1');
  });

  it('includes MP standards when excludeMP is false', async () => {
    mockFetch(200, gradeData);
    const repo = new KnowledgeGraphApiRepository(API_KEY);
    const results = await repo.getStandardsByGrade('3', { excludeMP: false });
    expect(results.map((s) => s.statementCode)).toContain('3.MP.1');
  });

  it('sends correct x-api-key header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true, status: 200,
      json: () => Promise.resolve({ data: [] }),
      text: () => Promise.resolve('[]'),
    });
    vi.stubGlobal('fetch', fetchMock);
    const repo = new KnowledgeGraphApiRepository('my-secret-key');
    await repo.getStandardsByGrade('3');
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('academic-standards'),
      expect.objectContaining({ headers: { 'x-api-key': 'my-secret-key' } }),
    );
  });
});

// ---------------------------------------------------------------------------
// KnowledgeGraphJsonRepository
// ---------------------------------------------------------------------------

const JSON_DATA = {
  standards: [
    {
      caseIdentifierUUID: 'uuid-1',
      statementCode: '3.MD.C.7.d',
      description: 'Area additive',
      statementType: 'Standard',
      normalizedStatementType: 'Standard',
      gradeLevel: ['3'],
      learningComponents: [
        { description: 'Recognize area as additive' },
        { description: 'Find areas of rectilinear figures' },
      ],
    },
    {
      caseIdentifierUUID: 'uuid-2',
      statementCode: '3.OA.A.1',
      description: 'Interpret products',
      statementType: 'Standard',
      normalizedStatementType: 'Standard',
      gradeLevel: ['3'],
      learningComponents: [{ description: 'Interpret products of whole numbers' }],
    },
    {
      caseIdentifierUUID: 'uuid-mp',
      statementCode: '3.MP.1',
      description: 'Make sense of problems',
      statementType: 'Mathematical Practice',
      normalizedStatementType: 'Mathematical Practice',
      gradeLevel: ['3'],
      learningComponents: [],
    },
  ],
};

describe('KnowledgeGraphJsonRepository', () => {
  it('resolves standard code to uuid and description', async () => {
    const repo = new KnowledgeGraphJsonRepository(JSON_DATA);
    const info = await repo.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('uuid-1');
    expect(info.description).toBe('Area additive');
  });

  it('throws KnowledgeGraphError for missing standard', async () => {
    const repo = new KnowledgeGraphJsonRepository(JSON_DATA);
    await expect(repo.getStandardInfo('9.ZZ.Z.1')).rejects.toThrow(KnowledgeGraphError);
  });

  it('returns learning components by UUID', async () => {
    const repo = new KnowledgeGraphJsonRepository(JSON_DATA);
    const lcs = await repo.getLearningComponents('uuid-1');
    expect(lcs).toHaveLength(2);
    expect(lcs[0].description).toBe('Recognize area as additive');
  });

  it('returns empty array for UUID with no LCs', async () => {
    const repo = new KnowledgeGraphJsonRepository(JSON_DATA);
    expect(await repo.getLearningComponents('uuid-mp')).toHaveLength(0);
  });

  it('filters by grade and excludes MP by default', async () => {
    const repo = new KnowledgeGraphJsonRepository(JSON_DATA);
    const results = await repo.getStandardsByGrade('3');
    expect(results.map((s) => s.statementCode)).not.toContain('3.MP.1');
    expect(results).toHaveLength(2);
  });
});
