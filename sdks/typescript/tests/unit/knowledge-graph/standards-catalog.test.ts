import { describe, it, expect, vi, beforeEach } from 'vitest';
import { StandardsCatalog } from '../../../src/knowledge-graph/standards-catalog.js';
import { Jurisdiction } from '../../../src/knowledge-graph/types.js';
import { ConfigurationError, AuthenticationError, InputValidationError } from '../../../src/errors.js';

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

function errorResponse(status: number, body = 'error') {
  return {
    ok: false,
    status,
    headers: new Headers({ 'content-type': 'application/json' }),
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(body),
  };
}

beforeEach(() => { vi.unstubAllGlobals(); });

const API_KEY = 'test-key';
const catalog = () => new StandardsCatalog({ platformApiKey: API_KEY, academicSubject: 'Mathematics' });

/** One learning component per identifier, in the paginated shape the LC endpoint returns. */
function lcPage(...identifiers: string[]) {
  return {
    data: identifiers.map((identifier) => ({ identifier, description: `LC ${identifier}` })),
    pagination: { hasMore: false, nextCursor: null },
  };
}

/**
 * Resolution reads the search endpoint and then the learning components of each
 * candidate, so tests must answer both. `lcsByUuid` maps a candidate uuid to its
 * learning-component identifiers; a uuid absent from the map has none.
 */
function stubResolution(candidates: unknown[], lcsByUuid: Record<string, string[]> = {}) {
  const fetchMock = vi.fn().mockImplementation((req: Request) => {
    const { url } = req;
    if (url.includes('/learning-components')) {
      const uuid = decodeURIComponent(url.split('/academic-standards/')[1].split('/')[0]);
      return Promise.resolve(okResponse(lcPage(...(lcsByUuid[uuid] ?? []))));
    }
    return Promise.resolve(okResponse(candidates));
  });
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

describe('StandardsCatalog - construction', () => {
  it.each(['', '   '])('throws ConfigurationError for a blank platform API key (%j)', (platformApiKey) => {
    expect(() => new StandardsCatalog({ platformApiKey })).toThrow(ConfigurationError);
  });

  it.each([0, -1, 2.5])('rejects concurrency %s with a clear error rather than a p-limit crash', (concurrency) => {
    expect(() => new StandardsCatalog({ platformApiKey: API_KEY, concurrency })).toThrow(
      /concurrency must be a positive integer/,
    );
  });

  it.each(['   ', 'x'.repeat(51)])(
    'getStandard rejects a code the KG cannot answer for (%j) without a request',
    async (code) => {
      const fetchMock = vi.fn();
      vi.stubGlobal('fetch', fetchMock);
      await expect(catalog().getStandard(code)).rejects.toThrow(InputValidationError);
      expect(fetchMock).not.toHaveBeenCalled();
    },
  );

  it('treats a whitespace-only academicSubject as absent rather than filtering on it', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({ data: [], pagination: { hasMore: false } }));
    vi.stubGlobal('fetch', fetchMock);
    await new StandardsCatalog({ platformApiKey: API_KEY, academicSubject: '   ' }).listStandards('3');
    expect((fetchMock.mock.calls[0][0] as Request).url).not.toContain('academicSubject');
  });
});

describe('StandardsCatalog - listStandards', () => {
  it('returns standards for a grade and applies the subject filter', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({
      data: [{ caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.D', gradeLevel: ['3'] }],
      pagination: { hasMore: false, nextCursor: null },
    }));
    vi.stubGlobal('fetch', fetchMock);

    const results = await catalog().listStandards('3');
    expect(results).toHaveLength(1);
    expect(results[0].statementCode).toBe('3.MD.C.7.D');
    const url = (fetchMock.mock.calls[0][0] as Request).url;
    expect(url).toContain('academicSubject=Mathematics');
    expect(url).toContain('normalizedStatementType=Standard');
  });

  it('accumulates across cursor pages', async () => {
    let call = 0;
    vi.stubGlobal('fetch', vi.fn().mockImplementation(() => {
      call++;
      return Promise.resolve(okResponse({
        data: [{ caseIdentifierUUID: `u${call}`, statementCode: `3.MD.C.7.${call}`, gradeLevel: ['3'] }],
        pagination: { hasMore: call === 1, nextCursor: call === 1 ? 'p2' : null },
      }));
    }));
    const results = await catalog().listStandards('3');
    expect(results).toHaveLength(2);
  });

  it('resolves a non-Multi-State framework before listing', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(okResponse({ data: [{ caseIdentifierUUID: 'tx-framework' }] }))
      .mockResolvedValueOnce(okResponse({ data: [], pagination: { hasMore: false, nextCursor: null } }));
    vi.stubGlobal('fetch', fetchMock);

    await catalog().listStandards('3', { jurisdiction: Jurisdiction.Texas });
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('/standards-frameworks');
    expect((fetchMock.mock.calls[1][0] as Request).url).toContain('tx-framework');
  });

  it('per-call academicSubject overrides the catalog default', async () => {
    const fetchMock = vi.fn().mockResolvedValue(okResponse({ data: [], pagination: { hasMore: false } }));
    vi.stubGlobal('fetch', fetchMock);
    await catalog().listStandards('3', { academicSubject: 'English Language Arts' });
    expect((fetchMock.mock.calls[0][0] as Request).url).toContain('academicSubject=English%20Language%20Arts');
  });
});

describe('StandardsCatalog - validateCodes', () => {
  it('resolves a known code and echoes the description', async () => {
    stubResolution([{ caseIdentifierUUID: 'u1', description: 'Recognize area as additive' }], { u1: ['lc-1'] });
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('resolved');
    expect(result.input).toBe('3.MD.C.7.d');
    expect(result.normalizedCode).toBe('3.MD.C.7.D');
    expect(result.uuid).toBe('u1');
    expect(result.description).toBe('Recognize area as additive');
  });

  it('reports the KG canonical spelling, not the uppercased lookup key', async () => {
    stubResolution([{ caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d' }], { u1: ['lc-1'] });
    const [result] = await catalog().validateCodes(['3.md.c.7.D']);
    expect(result.statementCode).toBe('3.MD.C.7.d');
    expect(result.normalizedCode).toBe('3.MD.C.7.D');
  });

  it('marks an unknown code not-found without throwing', async () => {
    stubResolution([]);
    const [result] = await catalog().validateCodes(['X.YZ.A.1']);
    expect(result.status).toBe('not-found');
    expect(result.error).toContain('Standard not found');
    expect(result.uuid).toBeUndefined();
  });

  it('reports every bad code rather than failing on the first', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((req: Request) => {
      if (req.url.includes('/learning-components')) return Promise.resolve(okResponse(lcPage('lc-1')));
      return Promise.resolve(req.url.includes('GOOD') ? okResponse([{ caseIdentifierUUID: 'u1' }]) : okResponse([]));
    }));
    const results = await catalog().validateCodes(['BAD.1', 'GOOD.1', 'BAD.2']);
    expect(results.map((r) => r.status)).toEqual(['not-found', 'resolved', 'not-found']);
  });

  it('discards candidates with no learning components and resolves the survivor', async () => {
    stubResolution(
      [{ caseIdentifierUUID: 'empty' }, { caseIdentifierUUID: 'populated', description: 'the real one' }],
      { populated: ['lc-1', 'lc-2'] },
    );
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('resolved');
    expect(result.uuid).toBe('populated');
    expect(result.description).toBe('the real one');
  });

  it('treats candidates sharing a learning-component set as interchangeable', async () => {
    stubResolution([{ caseIdentifierUUID: 'a' }, { caseIdentifierUUID: 'b' }], {
      a: ['lc-1', 'lc-2'],
      b: ['lc-2', 'lc-1'],
    });
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('resolved');
    expect(result.candidates).toBeUndefined();
  });

  it('offers one candidate per distinct component set, not per matching standard', async () => {
    // 'dup' shares sec-1's component set, so it is not a separate choice and must
    // not inflate either the candidate list or the count in the message.
    stubResolution(
      [
        { caseIdentifierUUID: 'sec-1', description: 'Graph exponential functions' },
        { caseIdentifierUUID: 'dup', description: 'Graph exponential functions, other course' },
        { caseIdentifierUUID: 'precalc', description: 'Define a curve parametrically' },
      ],
      { 'sec-1': ['lc-1'], dup: ['lc-1'], precalc: ['lc-9', 'lc-8'] },
    );
    const [result] = await catalog().validateCodes(['F.IF.7.b']);
    expect(result.status).toBe('ambiguous');
    expect(result.candidates?.map((c) => c.uuid)).toEqual(['sec-1', 'precalc']);
    expect(result.candidates?.map((c) => c.learningComponentCount)).toEqual([1, 2]);
    expect(result.error).toContain('Matched 2 standards');
    expect(result.error).toContain('pass a uuid');
  });

  it('distinguishes a standard with no learning components from a bad code', async () => {
    stubResolution([{ caseIdentifierUUID: 'u1', description: 'real but unauthored' }]);
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('no-learning-components');
    expect(result.uuid).toBe('u1');
    expect(result.error).toContain('No learning components');
  });

  it('flags a candidate list that hit the search limit as possibly truncated', async () => {
    const many = Array.from({ length: 50 }, (_, i) => ({ caseIdentifierUUID: `u${i}` }));
    stubResolution(many, { u0: ['lc-1'] });
    const [result] = await catalog().validateCodes(['PS.7']);
    expect(result.status).toBe('resolved');
    expect(result.truncated).toBe(true);
  });

  it('will not claim no-learning-components when the candidate list was capped', async () => {
    // An unseen candidate past the cap may carry components, so the definitive
    // answer is unsupportable.
    const many = Array.from({ length: 50 }, (_, i) => ({ caseIdentifierUUID: `u${i}` }));
    stubResolution(many);
    const [result] = await catalog().validateCodes(['PS.7']);
    expect(result.status).toBe('unchecked');
    expect(result.truncated).toBe(true);
    expect(result.error).toContain('capped');
  });

  it('rejects an over-long code locally without issuing a request', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const [result] = await catalog().validateCodes(['x'.repeat(51)]);
    expect(result.status).toBe('not-found');
    expect(result.error).toContain('exceeds 50 characters');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('dedupes case and whitespace variants to one request and one result', async () => {
    const fetchMock = stubResolution([{ caseIdentifierUUID: 'u1' }], { u1: ['lc-1'] });
    const results = await catalog().validateCodes(['3.MD.C.7.d', '3.md.c.7.D', '  3.MD.C.7.D  ']);
    expect(results).toHaveLength(1);
    // One search plus one learning-component fetch, both cached across variants.
    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(results[0].input).toBe('3.MD.C.7.d');
  });

  it('preserves input order of distinct codes', async () => {
    stubResolution([{ caseIdentifierUUID: 'u1' }], { u1: ['lc-1'] });
    const results = await catalog().validateCodes(['C.3', 'A.1', 'B.2']);
    expect(results.map((r) => r.normalizedCode)).toEqual(['C.3', 'A.1', 'B.2']);
  });

  it('marks an empty code not-found without issuing a request', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    const [result] = await catalog().validateCodes(['   ']);
    expect(result.status).toBe('not-found');
    expect(result.error).toContain('empty');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('stops issuing lookups once a fatal error is seen', async () => {
    const fetchMock = vi.fn().mockResolvedValue(errorResponse(401, 'Unauthorized'));
    vi.stubGlobal('fetch', fetchMock);
    const codes = Array.from({ length: 40 }, (_, i) => `CODE.${i}`);

    await expect(
      new StandardsCatalog({ platformApiKey: API_KEY, concurrency: 2 }).validateCodes(codes),
    ).rejects.toThrow(AuthenticationError);

    // Without the early abort every one of the 40 codes would have been requested.
    expect(fetchMock.mock.calls.length).toBeLessThan(codes.length);
  });

  it('propagates authentication failures instead of blaming the code', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(errorResponse(401, 'Unauthorized')));
    await expect(catalog().validateCodes(['3.MD.C.7.d'])).rejects.toThrow(AuthenticationError);
  });

  it('marks a rate-limited code unchecked rather than invalid', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(errorResponse(429, 'Too Many Requests')));
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('unchecked');
    expect(result.error).toContain('rate limit');
  });

  it('marks a server error unchecked rather than invalid', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(errorResponse(500, 'Server Error')));
    const [result] = await catalog().validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('unchecked');
  });

  it('points a 400 at the request filters rather than blaming the code', async () => {
    // The realistic cause is an unrecognised academicSubject, which fails for every
    // code — so "we could not check this" alone would send the user hunting the code.
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(errorResponse(400, 'Bad Request')));
    const [result] = await new StandardsCatalog({ platformApiKey: API_KEY, academicSubject: 'Maths' })
      .validateCodes(['3.MD.C.7.d']);
    expect(result.status).toBe('unchecked');
    expect(result.error).toContain('academicSubject');
  });

  it('keeps results for codes that resolved when another code hits a transient failure', async () => {
    vi.stubGlobal('fetch', vi.fn().mockImplementation((req: Request) =>
      req.url.includes('/learning-components')
        ? Promise.resolve(okResponse(lcPage('lc-1')))
        : Promise.resolve(
            req.url.includes('FLAKY')
              ? errorResponse(503, 'Service Unavailable')
              : okResponse([{ caseIdentifierUUID: 'u1' }]),
          ),
    ));
    const results = await catalog().validateCodes(['GOOD.1', 'FLAKY.1', 'GOOD.2']);
    expect(results.map((r) => r.status)).toEqual(['resolved', 'unchecked', 'resolved']);
  });

  it('returns an empty array for no input', async () => {
    const fetchMock = vi.fn();
    vi.stubGlobal('fetch', fetchMock);
    expect(await catalog().validateCodes([])).toEqual([]);
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
