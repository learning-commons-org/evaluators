import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import {
  KnowledgeGraphError,
  AuthenticationError,
  RateLimitError,
  NetworkError,
  RequestTimeoutError,
  StandardNotFoundError,
  InputValidationError,
} from '../../../src/errors.js';

// openapi-fetch calls response.text() when there is no Content-Length header,
// then JSON.parse()s the result. Both text and json must reflect the same body.
function okResponse(body: unknown) {
  const text = JSON.stringify(body);
  return {
    ok: true,
    status: 200,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(text),
  };
}

function mockFetch(status: number, body: unknown) {
  const text = typeof body === 'string' ? body : JSON.stringify(body);
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
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

  it('throws StandardNotFoundError when no standard found', async () => {
    mockFetch(200, []);
    const call = new KnowledgeGraphClient(API_KEY).getStandardInfo('X.YZ.A.1');
    await expect(call).rejects.toThrow(StandardNotFoundError);
    await expect(call).rejects.toBeInstanceOf(InputValidationError);
  });

  it('returns the first match and flags ambiguity when a code matches multiple standards', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'a' }, { caseIdentifierUUID: 'b' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('a');
    expect(info.ambiguous).toBe(true);
  });

  it('does not flag ambiguity for a single match', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'a' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect(info.ambiguous).toBeUndefined();
  });

  it('requests the search endpoint maximum, since its default of 5 would truncate', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('limit=50');
  });

  it('normalizes the code for lookup: uppercases, trims, collapses interior whitespace', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('  3.md.c\t7.d  ');
    expect(info.normalizedCode).toBe('3.MD.C 7.D');
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('statementCode=3.MD.C%207.D');
  });

  it('collapses a run of interior whitespace to a single space', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'u1' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C \t 7.D');
    expect(info.normalizedCode).toBe('3.MD.C 7.D');
  });

  it('defaults the jurisdiction to Multi-State', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('jurisdiction=Multi-State');
  });

  it('exposes every candidate, not just the chosen one', async () => {
    mockFetch(200, [
      { caseIdentifierUUID: 'a', statementCode: 'F.IF.7.b', description: 'Graph exponential functions' },
      { caseIdentifierUUID: 'b', statementCode: 'F.IF.7.b', description: 'Graph piecewise-defined functions' },
      { caseIdentifierUUID: 'c', statementCode: 'F.IF.7.b', description: 'Define a curve parametrically' },
    ]);
    const candidates = await new KnowledgeGraphClient(API_KEY).getStandardCandidates('F.IF.7.b');
    expect(candidates).toHaveLength(3);
    expect(candidates.map((c) => c.uuid)).toEqual(['a', 'b', 'c']);
    expect(candidates[1].description).toBe('Graph piecewise-defined functions');
    expect(candidates.every((c) => c.normalizedCode === 'F.IF.7.B')).toBe(true);
  });

  it('serves getStandardInfo and getStandardCandidates from one request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      okResponse([{ caseIdentifierUUID: 'a' }, { caseIdentifierUUID: 'b' }]),
    );
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    const info = await client.getStandardInfo('3.MD.C.7.d');
    const candidates = await client.getStandardCandidates('3.MD.C.7.d');
    expect(info.ambiguous).toBe(true);
    expect(candidates).toHaveLength(2);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  
  it('survives a caller mutating the returned candidate list', async () => {
    mockFetch(200, [
      { caseIdentifierUUID: 'a', description: 'first' },
      { caseIdentifierUUID: 'b', description: 'second' },
    ]);
    const client = new KnowledgeGraphClient(API_KEY);

    const first = await client.getStandardCandidates('3.MD.C.7.d');
    first.reverse();
    first[0].description = 'mutated';

    const second = await client.getStandardCandidates('3.MD.C.7.d');
    expect(second.map((c) => c.uuid)).toEqual(['a', 'b']);
    expect(second[0].description).toBe('first');
    expect((await client.getStandardInfo('3.MD.C.7.d')).uuid).toBe('a');
  });

  it('reports not-found using the code as the caller spelled it', async () => {
    mockFetch(200, []);
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.md.c.7.d').catch((e) => e);
    expect(err.message).toContain('"3.md.c.7.d"');
  });

  it('re-queries after an empty result rather than caching not-found', async () => {
    // An empty search response fulfils, so it bypasses the rejection-eviction path.
    // A transient empty (index warm-up, replica lag) must not poison the code.
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okResponse([]))
      .mockResolvedValue(okResponse([{ caseIdentifierUUID: 'appeared-later' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);

    await expect(client.getStandardInfo('3.MD.C.7.d')).rejects.toThrow(/Standard not found/);
    const info = await client.getStandardInfo('3.MD.C.7.d');

    expect(info.uuid).toBe('appeared-later');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('gives concurrent callers their own spelling in the not-found error', async () => {
    // Both share one in-flight request, so the message cannot be built inside it.
    const fetchMock = vi.fn().mockResolvedValue(okResponse([]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);

    const [lower, upper] = await Promise.all([
      client.getStandardInfo('3.md.c.7.d').catch((e) => e),
      client.getStandardInfo('3.MD.C.7.D').catch((e) => e),
    ]);

    expect(lower.message).toContain('"3.md.c.7.d"');
    expect(upper.message).toContain('"3.MD.C.7.D"');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('caches an omitted jurisdiction and an explicit Multi-State as one entry', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await client.getStandardInfo('3.MD.C.7.d');
    await client.getStandardInfo('3.MD.C.7.d', { jurisdiction: 'Multi-State' });
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('reports the KG canonical code, preserving lowercase sub-standard letters', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.md.c.7.D');
    expect(info.statementCode).toBe('3.MD.C.7.d');
    expect(info.normalizedCode).toBe('3.MD.C.7.D');
  });

  it('falls back to the normalized code when the KG omits statementCode', async () => {
    mockFetch(200, [{ caseIdentifierUUID: 'u1' }]);
    const info = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.md.c.7.d');
    expect(info.statementCode).toBe('3.MD.C.7.D');
  });

  it('collapses case and whitespace variants onto one cached request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await Promise.all([
      client.getStandardInfo('3.MD.C.7.d'),
      client.getStandardInfo('3.md.c.7.D'),
      client.getStandardInfo('  3.MD.C.7.D  '),
    ]);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('does not collide cache entries across academicSubject', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await client.getStandardInfo('3.MD.C.7.d', { academicSubject: 'Mathematics' });
    await client.getStandardInfo('3.MD.C.7.d', { academicSubject: 'English Language Arts' });
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it.each([401, 403])('throws AuthenticationError on %i', async (status) => {
    mockFetch(status, 'Unauthorized');
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err.message).toContain('Unauthorized');
  });

  // Reading the body is best-effort: a failure there must not mask the status
  // we already know, nor leak "undefined" into the message.
  it('classifies by status when the error body cannot be read', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      headers: new Headers(),
      json: () => Promise.reject(new Error('stream closed')),
      text: () => Promise.reject(new Error('stream closed')),
    }));

    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.statusCode).toBe(503);
    // An unreadable body contributes nothing — not "undefined", not a placeholder.
    expect(err.message).toBe('Knowledge Graph request failed (503): ');
  });

  it('throws RateLimitError on 429', async () => {
    mockFetch(429, 'Too Many Requests');
    await expect(new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d')).rejects.toThrow(RateLimitError);
  });

  // Attribution and diagnostics are what let a caller tell a KG outage from an
  // LLM one, so they must survive the trip out of the middleware.
  it('attributes an HTTP failure to the knowledge graph, with status, request id and body', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: false,
      status: 429,
      headers: new Headers({ 'content-type': 'text/plain', 'x-request-id': 'req_kg' }),
      json: () => Promise.resolve('slow down'),
      text: () => Promise.resolve('slow down'),
    }));

    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(RateLimitError);
    expect(err.dependency).toBe('knowledge-graph');
    expect(err.statusCode).toBe(429);
    expect(err.requestId).toBe('req_kg');
    expect(err.message).toContain('slow down');
  });

  it('leaves requestId null when the response carries no request id', async () => {
    mockFetch(500, 'Server Error');
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err.requestId).toBeNull();
    expect(err.message).toContain('Server Error');
  });

  it('throws KnowledgeGraphError with statusCode on 500', async () => {
    mockFetch(500, 'Server Error');
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.statusCode).toBe(500);
  });

  it('throws NetworkError when fetch throws', async () => {
    const cause = new Error('ECONNREFUSED');
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(cause));
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.dependency).toBe('knowledge-graph');
    expect(err.cause).toBe(cause);
    expect(err.message).toContain('ECONNREFUSED');
  });

  it('bounds the request with a timeout signal', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d');

    // Without this the client would hang indefinitely on an unresponsive KG.
    expect(fetchMock.mock.calls[0][1]?.signal).toBeInstanceOf(AbortSignal);
  });

  it('reports a non-Error rejection rather than losing it', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue('socket hang up'));
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(NetworkError);
    expect(err.message).toContain('socket hang up');
  });

  // openapi-fetch parses the body itself, so a KG that answers 200 with
  // non-JSON surfaces as a SyntaxError from deep inside the client.
  it('wraps a malformed JSON body as a KnowledgeGraphError', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-type': 'application/json' }),
      text: () => Promise.resolve('<html>gateway</html>'),
      json: () => Promise.reject(new SyntaxError('Unexpected token <')),
    }));

    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.message).toContain('invalid JSON');
    expect(err.cause).toBeInstanceOf(SyntaxError);
  });

  it('throws RequestTimeoutError, not NetworkError, when AbortSignal fires', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new DOMException('aborted', 'TimeoutError')));
    const err = await new KnowledgeGraphClient(API_KEY).getStandardInfo('3.MD.C.7.d').catch((e) => e);
    expect(err).toBeInstanceOf(RequestTimeoutError);
    expect(err).not.toBeInstanceOf(NetworkError);
    expect(err.message).toContain('timed out');
    expect(err.dependency).toBe('knowledge-graph');
    expect(err.retryable).toBe(true);
  });

  it('sends x-api-key header', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient('my-secret-key').getStandardInfo('3.MD.C.7.d');
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.headers.get('x-api-key')).toBe('my-secret-key');
  });

  it('evicts cache on rejection so the next call retries', async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error('transient'))
      .mockResolvedValue(okResponse([{ caseIdentifierUUID: 'recovered' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await expect(client.getStandardInfo('3.MD.C.7.d')).rejects.toThrow();
    const info = await client.getStandardInfo('3.MD.C.7.d');
    expect(info.uuid).toBe('recovered');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it('caches successful lookups so repeated same-code calls fetch once', async () => {
    // Guarantees a batch of N items over M unique standards does M fetches,
    // not N (the standards family reuses one client across all rows).
    const fetchMock = vi.fn().mockResolvedValue(okResponse([{ caseIdentifierUUID: 'u1' }]));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await client.getStandardInfo('4.G.A.1');
    await client.getStandardInfo('4.G.A.1');
    await client.getStandardInfo('4.G.A.1');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe('KnowledgeGraphClient - getLearningComponents', () => {
  it('returns learning components', async () => {
    mockFetch(200, { data: [{ description: 'Recognize area as additive' }, { description: 'Find areas' }], pagination: { hasMore: false, nextCursor: null } });
    const lcs = await new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid-abc');
    expect(lcs).toHaveLength(2);
    expect(lcs[0].description).toBe('Recognize area as additive');
  });

  it('filters out null descriptions but reports how many were dropped', async () => {
    mockFetch(200, { data: [{ description: 'Valid' }, { description: null }, { description: 'Also valid' }], pagination: { hasMore: false, nextCursor: null } });
    // The count is what lets a caller say "components exist but are undescribed"
    // instead of "nothing is authored against this standard".
    const set = await new KnowledgeGraphClient(API_KEY).getLearningComponentSet('uuid-abc');
    expect(set.components).toHaveLength(2);
    expect(set.undescribedCount).toBe(1);
  });

  it('reports undescribedCount with no evaluable components at all', async () => {
    mockFetch(200, { data: [{ description: null }, { description: null }], pagination: { hasMore: false, nextCursor: null } });
    const set = await new KnowledgeGraphClient(API_KEY).getLearningComponentSet('uuid-abc');
    expect(set.components).toEqual([]);
    expect(set.undescribedCount).toBe(2);
  });

  it('follows cursor pagination across pages, sending the cursor and the uuid', async () => {
    let call = 0;
    const fetchMock = vi.fn().mockImplementation(() => {
      call++;
      const body = { data: [{ description: `LC ${call}` }, { description: null }], pagination: { hasMore: call === 1, nextCursor: call === 1 ? 'page-2' : null } };
      return Promise.resolve(okResponse(body));
    });
    vi.stubGlobal('fetch', fetchMock);
    const set = await new KnowledgeGraphClient(API_KEY).getLearningComponentSet('uuid-abc');
    expect(set.components).toHaveLength(2);
    // Accumulated across pages, not reset per page.
    expect(set.undescribedCount).toBe(2);
    expect(call).toBe(2);
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('uuid-abc');
    expect((fetchMock.mock.calls[0][0] as Request).url).not.toContain('cursor=');
    expect((fetchMock.mock.calls[1][0] as Request).url).toContain('cursor=page-2');
  });

  it('serves a repeated uuid from cache', async () => {
    const body = { data: [{ description: 'LC one' }], pagination: { hasMore: false, nextCursor: null } };
    const fetchMock = vi.fn().mockResolvedValue(okResponse(body));
    vi.stubGlobal('fetch', fetchMock);
    const client = new KnowledgeGraphClient(API_KEY);
    await Promise.all([client.getLearningComponents('uuid-abc'), client.getLearningComponents('uuid-abc')]);
    await client.getLearningComponents('uuid-abc');
    // Both accessors share one cache entry, so asking for the count is free.
    await client.getLearningComponentSet('uuid-abc');
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it('throws KnowledgeGraphError if hasMore=true but nextCursor is null', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: true, nextCursor: null } });
    await expect(new KnowledgeGraphClient(API_KEY).getLearningComponents('uuid')).rejects.toThrow(KnowledgeGraphError);
  });

  it('evicts LC cache on rejection so the next call retries', async () => {
    const body = { data: [{ description: 'Recovered LC' }], pagination: { hasMore: false, nextCursor: null } };
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(new Error('transient 503'))
      .mockResolvedValue(okResponse(body));
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
    const body = { data: [{ caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', normalizedStatementType: 'Standard', gradeLevel: ['3'] }] };
    const fetchMock = vi.fn().mockResolvedValue(okResponse(body));
    vi.stubGlobal('fetch', fetchMock);
    const results = await new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3');
    const request = fetchMock.mock.calls[0][0] as Request;
    expect(request.url).toContain('normalizedStatementType=Standard');
    expect(results).toHaveLength(1);
    expect(results[0].statementCode).toBe('3.MD.C.7.d');
  });

  it('resolves Multi-State to the CCSS framework without a lookup request', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({ data: [], pagination: { hasMore: false } }));
    vi.stubGlobal('fetch', fetchMock);
    await new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3');
    expect(fetchMock).toHaveBeenCalledTimes(1);
    const url = (fetchMock.mock.calls[0][0] as Request).url;
    expect(url).toContain('/academic-standards?');
    expect(url).toContain('standardsFrameworkCaseIdentifierUUID=c6496676-d7cb-11e8-824f-0242ac160002');
  });

  it('follows cursor pagination across pages and accumulates all standards', async () => {
    let call = 0;
    const fetchMock = vi.fn().mockImplementation(() => {
      call++;
      return Promise.resolve(okResponse({
        data: [{ caseIdentifierUUID: `u${call}`, statementCode: `3.MD.C.7.${call}`, gradeLevel: ['3'] }],
        pagination: { hasMore: call < 3, nextCursor: call < 3 ? `page-${call + 1}` : null },
      }));
    });
    vi.stubGlobal('fetch', fetchMock);
    const results = await new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3');
    expect(results).toHaveLength(3);
    expect(results.map((r) => r.statementCode)).toEqual(['3.MD.C.7.1', '3.MD.C.7.2', '3.MD.C.7.3']);
    expect(fetchMock).toHaveBeenCalledTimes(3);
    expect((fetchMock.mock.calls[1][0] as Request).url).toContain('cursor=page-2');
    expect((fetchMock.mock.calls[0][0] as Request).url).not.toContain('cursor=');
  });

  it('throws KnowledgeGraphError if hasMore=true but nextCursor is null', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: true, nextCursor: null } });
    await expect(new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3'))
      .rejects.toThrow(KnowledgeGraphError);
  });

  it('throws KnowledgeGraphError if the API repeats a cursor', async () => {
    mockFetch(200, { data: [], pagination: { hasMore: true, nextCursor: 'same-page' } });
    const err = await new KnowledgeGraphClient(API_KEY).getStandardsByGrade('3').catch((e) => e);
    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.message).toContain('repeated');
  });
});

describe('KnowledgeGraphClient - getLearningComponentsByCode', () => {
  it('chains standard info lookup then LC fetch', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okResponse([{ caseIdentifierUUID: 'test-uuid', description: 'Area additive' }]))
      .mockResolvedValueOnce(okResponse({ data: [{ description: 'LC one' }], pagination: { hasMore: false, nextCursor: null } }));
    vi.stubGlobal('fetch', fetchMock);
    const result = await new KnowledgeGraphClient(API_KEY).getLearningComponentsByCode('3.MD.C.7.d');
    expect(result.uuid).toBe('test-uuid');
    expect(result.description).toBe('Area additive');
    expect(result.components[0].description).toBe('LC one');
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  });
