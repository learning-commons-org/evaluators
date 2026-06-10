import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import { KnowledgeGraphError, AuthenticationError, RateLimitError, NetworkError } from '../../../src/errors.js';

function mockFetch(status: number, body: unknown) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(text),
  }));
}

beforeEach(() => { vi.unstubAllGlobals(); });

const API_KEY = 'test-key';

describe('KnowledgeGraphClient - getStandardInfo', () => {
  it('returns uuid and description for an exact match', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'abc-123', description: 'Recognize area as additive' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('abc-123');
    expect(info.description).toBe('Recognize area as additive');
  });

  it('returns uuid with no description when absent from response', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'abc-123' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('abc-123');
    expect(info.description).toBeUndefined();
  });

  it('throws KnowledgeGraphError when no standard found', async () => {
    mockFetch(200, []);
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('X.YZ.A.1')).rejects.toThrow(KnowledgeGraphError);
  });

  it('throws KnowledgeGraphError when ambiguous (>1 results)', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'a' }, { caseIdentifierUUID: 'b' }]);
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD')).rejects.toThrow('Ambiguous');
  });

  it('throws AuthenticationError on 401', async () => {
    mockFetch(401, 'Unauthorized');
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d')).rejects.toThrow(AuthenticationError);
  });

  it('throws RateLimitError on 429', async () => {
    mockFetch(429, 'Too Many Requests');
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d')).rejects.toThrow(RateLimitError);
  });

  it('throws KnowledgeGraphError with statusCode on 500', async () => {
    mockFetch(500, 'Server Error');
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.statusCode).toBe(500);
  });

  it('throws NetworkError when fetch throws', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d')).rejects.toThrow(NetworkError);
  });

  it('throws NetworkError with timeout message when AbortSignal fires', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('aborted', 'TimeoutError')));
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.message).toContain('timed out');
  });

  it('sends x-api-key header', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve([{ caseIdentifierUUID: 'u1' }]), text: () => Promise.resolve('') });
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient('my-secret-key').getStandardInfo('3.MD.C.7.d');
    expect(fetchMock.mock.calls[0][1]).toMatchObject({ headers: { 'x-api-key': 'my-secret-key' } });
  });

  it('evicts cache on rejection so the next call retries', async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error('transient'))
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve([{ caseIdentifierUUID: 'recovered' }]), text: () => Promise.resolve('') });
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await expect(client.getStandardInfo('3.MD.C.7.d')).rejects.toThrow();
    const info = await client.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('recovered');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe('KnowledgeGraphClient - getLearningComponents', () => {
  it('returns learning components', async () => {
    mockFetch(200, { data: [{ description: 'Recognize area as additive' }, { description: 'Find areas' }], pagination: { hasMore: false, nextCursor: null } });
    const lcs = await new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid-abc');
    expect(lcs).toHaveLength(2);
    expect(lcs[0].description).toBe('Recognize area as additive');
  });

  it('filters out null descriptions', async () => {
    mockFetch(200, { data: [{ description: 'Valid' }, { description: null }, { description: 'Also valid' }], pagination: { hasMore: false, nextCursor: null } });
    const lcs = await new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid-abc');
    expect(lcs).toHaveLength(2);
  });

  it('follows cursor pagination across pages', async () => {
    let call = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => {
      call++;
      return Promise.resolve({ ok: true, status: 200, json: () => Promise.resolve({ data: [{ description: `LC ${call}` }], pagination: { hasMore: call === 1, nextCursor: call === 1 ? 'page-2' : null } }), text: () => Promise.resolve('') });
    }));
    const lcs = await new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid-abc');
    expect(lcs).toHaveLength(2);
    expect(call).toBe(2);
  });

  it('throws KnowledgeGraphError if hasMore=true but nextCursor is null', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: true, nextCursor: null } });
    await expect(new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid')).rejects.toThrow(KnowledgeGraphError);
  });

  it('evicts LC cache on rejection so the next call retries', async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error('transient 503'))
      .mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ data: [{ description: 'Recovered LC' }], pagination: { hasMore: false, nextCursor: null } }), text: () => Promise.resolve('') });
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await expect(client.getLearningComponents('uuid-abc')).rejects.toThrow();
    const lcs = await client.getLearningComponents('uuid-abc');
    expect(lcs[0].description).toBe('Recovered LC');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});

describe('KnowledgeGraphClient - getStandardsByGrade', () => {
  it('returns standards filtered to normalizedStatementType=Standard via URL', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, json: () => Promise.resolve({ data: [
      { caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
    ] }), text: () => Promise.resolve('') });
    vi.stubGlobal('fetch', fetchMock);
    const results = await new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3');
    expect(fetchMock.mock.calls[0][0]).toContain('normalizedStatementType=Standard');
    expect(results).toHaveLength(1);
    expect(results[0].statementCode).toBe('3.MD.C.7.d');
  });

  it('throws KnowledgeGraphError if hasMore=true (pagination not implemented for standards)', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: true, nextCursor: 'page-2' } });
    await expect(new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3'))
      .rejects.toThrow(KnowledgeGraphError);
  });
});

describe('KnowledgeGraphClient - getLearningComponentsByCode', () => {
  it('chains standard info lookup then LC fetch', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve([{ caseIdentifierUUID: 'test-uuid', description: 'Area additive' }]), text: () => Promise.resolve('') })
      .mockResolvedValueOnce({ ok: true, status: 200, json: () => Promise.resolve({ data: [{ description: 'LC one' }], pagination: { hasMore: false, nextCursor: null } }), text: () => Promise.resolve('') });
    vi.stubGlobal('fetch', fetchMock);
    const result = await new KnowledgeGraphClient(API_KEY).getLearningComponentsByCode('3.MD.C.7.d');
    expect(result.uuid).toBe('test-uuid');
    expect(result.description).toBe('Area additive');
    expect(result.components[0].description).toBe('LC one');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
