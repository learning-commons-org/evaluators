import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KnowledgeGraphClient } from '../../../src/knowledge-graph/client.js';
import { InputValidationError } from '../../../src/errors.js';

const API_KEY = 'test-key';
const CODE = 'HSN-RN.B.3';
const EMPTY_COPY = { uuid: 'empty-copy', statementCode: CODE, normalizedCode: CODE, description: 'no LCs' };
const POPULATED_COPY = { uuid: 'populated-copy', statementCode: CODE, normalizedCode: CODE, description: 'with LCs' };
const LCS = [{ identifier: 'lc-1', description: 'Rewrite exponents' }];

function clientWith(candidates: unknown[], componentsByUuid: Record<string, unknown[]>) {
  const client = new KnowledgeGraphClient(API_KEY);
  vi.spyOn(client, 'getStandardCandidates').mockResolvedValue(candidates as never);
  vi.spyOn(client, 'getLearningComponents').mockImplementation(
    async (uuid: string) => (componentsByUuid[uuid] ?? []) as never,
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

  it('chooses a readable populated copy when another copy cannot be read', async () => {
    const client = new KnowledgeGraphClient(API_KEY);
    vi.spyOn(client, 'getStandardCandidates').mockResolvedValue([
      EMPTY_COPY,
      POPULATED_COPY,
      { ...EMPTY_COPY, uuid: 'broken' },
    ] as never);
    vi.spyOn(client, 'getLearningComponents').mockImplementation(async (uuid: string) => {
      if (uuid === 'broken') throw new Error('KG 503');
      return (uuid === 'populated-copy' ? LCS : []) as never;
    });

    const result = await client.getLearningComponentsByCode(CODE);

    expect(result.uuid).toBe('populated-copy');
  });

  it('fails only when no copy can be read', async () => {
    const client = clientWith([EMPTY_COPY, { ...EMPTY_COPY, uuid: 'other' }], {});
    vi.spyOn(client, 'getLearningComponents').mockRejectedValue(new Error('KG 503'));

    await expect(client.getLearningComponentsByCode(CODE)).rejects.toThrow('KG 503');
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

  it('refuses a malformed UUID before making a request', async () => {
    const fetchMock = mockFetch(200, {});

    await expect(new KnowledgeGraphClient(API_KEY).getAcademicStandard('not-a-uuid'))
      .rejects.toBeInstanceOf(InputValidationError);
    expect(fetchMock).not.toHaveBeenCalled();
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
