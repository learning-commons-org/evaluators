import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import { InputValidationError, KnowledgeGraphError } from '../../../src/errors.js';

const API_KEY = 'test-key';
const CODE = 'HSN-RN.B.3';
const EMPTY_COPY = { uuid: 'empty-copy', statementCode: CODE, normalizedCode: CODE, description: 'no LCs' };
const POPULATED_COPY = { uuid: 'populated-copy', statementCode: CODE, normalizedCode: CODE, description: 'with LCs' };
const LCS = [{ identifier: 'lc-1', description: 'Rewrite exponents' }];

function clientWith(candidates: unknown[], componentsByUuid: Record<string, unknown[]>) {
  const client = new KnowledgeGraphClient(API_KEY);
  vi.spyOn(client, 'getStandardCandidates').mockResolvedValue(candidates as never);
  vi.spyOn(client, 'getLearningComponentSet').mockImplementation(
    async (uuid: string) => ({ components: componentsByUuid[uuid] ?? [], undescribedCount: 0 }) as never,
  );
  return client;
}

describe('KnowledgeGraphClient - getLearningComponentsByCode with several matches', () => {
  beforeEach(() => { vi.restoreAllMocks(); });

  it('chooses the match that has learning components over an empty first match', async () => {
    const client = clientWith([EMPTY_COPY, POPULATED_COPY], { 'populated-copy': LCS });

    const result = await client.getLearningComponentsByCode(CODE);

    expect(result.uuid).toBe('populated-copy');
    expect(result.components).toEqual(LCS);
    expect(result.ambiguous).toBe(true);
  });

  it('keeps the first of several matches that all have components', async () => {
    const second = { ...POPULATED_COPY, uuid: 'second-copy' };
    const client = clientWith([POPULATED_COPY, second], { 'populated-copy': LCS, 'second-copy': LCS });

    const result = await client.getLearningComponentsByCode(CODE);

    expect(result.uuid).toBe('populated-copy');
  });

  it('falls back to the first match, flagged ambiguous, when none has components', async () => {
    const client = clientWith([EMPTY_COPY, { ...EMPTY_COPY, uuid: 'other-empty' }], {});

    const result = await client.getLearningComponentsByCode(CODE);

    expect(result.uuid).toBe('empty-copy');
    expect(result.components).toEqual([]);
    expect(result.ambiguous).toBe(true);
  });

  it('fails when any copy cannot be read, rather than choosing among the rest', async () => {
    // The choice would otherwise depend on which requests happened to fail.
    const client = new KnowledgeGraphClient(API_KEY);
    vi.spyOn(client, 'getStandardCandidates').mockResolvedValue([
      EMPTY_COPY,
      POPULATED_COPY,
      { ...EMPTY_COPY, uuid: 'broken' },
    ] as never);
    vi.spyOn(client, 'getLearningComponentSet').mockImplementation(async (uuid: string) => {
      if (uuid === 'broken') throw new Error('KG 503');
      return { components: uuid === 'populated-copy' ? LCS : [], undescribedCount: 0 } as never;
    });

    await expect(client.getLearningComponentsByCode(CODE)).rejects.toThrow('KG 503');
  });

  it('fails when every copy cannot be read', async () => {
    const client = clientWith([EMPTY_COPY, { ...EMPTY_COPY, uuid: 'other' }], {});
    vi.spyOn(client, 'getLearningComponentSet').mockRejectedValue(new Error('KG 503'));

    await expect(client.getLearningComponentsByCode(CODE)).rejects.toThrow('KG 503');
  });

  it('does not judge an empty copy when the populated copy could not be read', async () => {
    const client = new KnowledgeGraphClient(API_KEY);
    vi.spyOn(client, 'getStandardCandidates').mockResolvedValue([EMPTY_COPY, POPULATED_COPY] as never);
    vi.spyOn(client, 'getLearningComponentSet').mockImplementation(async (uuid: string) => {
      if (uuid === 'populated-copy') throw new Error('KG 429');
      return { components: [], undescribedCount: 0 } as never;
    });

    const err = await client.getLearningComponentsByCode(CODE).catch((e) => e);
    expect(err?.message).toBe('KG 429');
  });

  it('refuses to judge an empty copy when the candidate list may be truncated', async () => {
    const capped = Array.from({ length: 50 }, (_, i) => ({ ...EMPTY_COPY, uuid: `copy-${i}` }));
    const client = clientWith(capped, {});

    await expect(client.getLearningComponentsByCode(CODE)).rejects.toThrow(/matched 50 or more standards.*could not be checked/);
  });

  it('does not flag a single match as ambiguous', async () => {
    const client = clientWith([POPULATED_COPY], { 'populated-copy': LCS });

    const result = await client.getLearningComponentsByCode(CODE);

    expect(result.ambiguous).toBeUndefined();
    expect(result.uuid).toBe('populated-copy');
  });
});

describe('KnowledgeGraphClient - getAcademicStandard', () => {
  beforeEach(() => { vi.unstubAllGlobals(); });

  function mockFetch(status: number, body: unknown) {
    const text = JSON.stringify(body);
    const fetchMock = vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      headers: new Headers({ 'content-type': 'application/json' }),
      json: () => Promise.resolve(body),
      text: () => Promise.resolve(text),
    });
    vi.stubGlobal('fetch', fetchMock);
    return fetchMock;
  }

  it('maps the standard the UUID names', async () => {
    mockFetch(200, {
      caseIdentifierUUID: '6ba25656-d7cc-11e8-824f-0242ac160002',
      statementCode: '3.MD.C.7.d',
      description: 'Recognize area as additive.',
      academicSubject: 'Mathematics',
    });

    const standard = await new KnowledgeGraphClient(API_KEY).getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002');

    expect(standard).toEqual({
      uuid: '6ba25656-d7cc-11e8-824f-0242ac160002',
      statementCode: '3.MD.C.7.d',
      description: 'Recognize area as additive.',
      academicSubject: 'Mathematics',
    });
  });

  it('reads a sparse standard as nulls rather than failing', async () => {
    mockFetch(200, { caseIdentifierUUID: '6ba25656-d7cc-11e8-824f-0242ac160002' });

    const standard = await new KnowledgeGraphClient(API_KEY).getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002');

    expect(standard.statementCode).toBeNull();
    expect(standard.description).toBeNull();
    expect(standard.academicSubject).toBeNull();
  });

  it('requests the standard at its own UUID path', async () => {
    const fetchMock = mockFetch(200, { caseIdentifierUUID: '6ba25656-d7cc-11e8-824f-0242ac160002' });

    await new KnowledgeGraphClient(API_KEY).getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002');

    expect(fetchMock.mock.calls[0][0].url).toContain('/academic-standards/6ba25656-d7cc-11e8-824f-0242ac160002');
  });

  it('refuses a malformed UUID before making a request', async () => {
    const fetchMock = mockFetch(200, {});

    const err = await new KnowledgeGraphClient(API_KEY).getAcademicStandard('not-a-uuid').catch((e) => e);

    expect(err).toBeInstanceOf(InputValidationError);
    expect(err.message).toContain('"not-a-uuid"');
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it('treats an empty response as a Knowledge Graph error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      headers: new Headers({ 'content-length': '0' }),
      json: () => Promise.resolve(undefined),
      text: () => Promise.resolve(''),
    }));

    const err = await new KnowledgeGraphClient(API_KEY)
      .getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002')
      .catch((e) => e);

    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err.message).toContain('Unexpected empty response');
  });

  it('reports a server error as a Knowledge Graph error, not an input error', async () => {
    mockFetch(500, { message: 'boom' });

    const err = await new KnowledgeGraphClient(API_KEY)
      .getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002')
      .catch((e) => e);

    expect(err).toBeInstanceOf(KnowledgeGraphError);
    expect(err).not.toBeInstanceOf(InputValidationError);
  });

  it('reports a UUID the Knowledge Graph does not hold as an input error', async () => {
    mockFetch(404, { message: 'not found' });

    const err = await new KnowledgeGraphClient(API_KEY)
      .getAcademicStandard('6ba25656-d7cc-11e8-824f-0242ac160002')
      .catch((e) => e);

    expect(err).toBeInstanceOf(InputValidationError);
    expect(err.message).toContain('6ba25656-d7cc-11e8-824f-0242ac160002');
  });
});
