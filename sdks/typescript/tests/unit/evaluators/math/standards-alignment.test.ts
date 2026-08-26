import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
  type MathStandardsAlignmentEvaluatorConfig,
} from '../../../../src/evaluators/math/standards-alignment.js';
import { ConfigurationError, InputValidationError, LLMOutputProcessingError, KnowledgeGraphError, RateLimitError } from '../../../../src/errors.js';
import type { LLMProvider } from '../../../../src/providers/base.js';
import type { KnowledgeGraphClient } from '../../../../src/knowledge-graph/client.js';

// ---------------------------------------------------------------------------
// Shared mock provider
// ---------------------------------------------------------------------------

const mockProvider: LLMProvider = {
  label: 'mock:model',
  generateStructured: vi.fn(),
  generateText: vi.fn(),
};

vi.mock('../../../../src/providers/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...(actual as object), createProvider: vi.fn(() => mockProvider) };
});

vi.mock('../../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

// ---------------------------------------------------------------------------
// Fixtures
// ---------------------------------------------------------------------------

const STATEMENT_CODE = '3.MD.C.7.d';
const JURISDICTION = Jurisdiction.MultiState;
const QUESTION =
  'A playground is shaped like an L. One rectangle is 8 ft × 3 ft, the other is 4 ft × 2 ft. ' +
  'What is the total area?';

const LC_COMPONENTS = [
  { identifier: 'lc-001', description: 'Recognize area as additive' },
  { identifier: 'lc-002', description: 'Find areas of rectilinear figures by decomposing into non-overlapping rectangles' },
];

const MOCK_BATCH_RESPONSE = {
  data: {
    evaluations: [
      { lc_id: 'lc-001', reasoning: 'The question asks students to add areas.', answer: 'Yes', feedback: '' },
      { lc_id: 'lc-002', reasoning: 'Students must decompose the L-shape.', answer: 'Yes', feedback: '' },
    ],
  },
  model: 'anthropic:claude-haiku-4-5-20251001',
  usage: { inputTokens: 300, outputTokens: 150 },
  latencyMs: 1200,
};

function makeMockKgClient(overrides: Partial<KnowledgeGraphClient> = {}): KnowledgeGraphClient {
  return {
    getStandardInfo: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', description: 'Recognize area as additive' }),
    getLearningComponents: vi.fn().mockResolvedValue(LC_COMPONENTS),
    getStandardsByGrade: vi.fn().mockResolvedValue([
      {
        caseIdentifierUUID: 'uuid-abc',
        statementCode: STATEMENT_CODE,
        description: 'Area additive',
        statementType: 'Standard',
        normalizedStatementType: 'Standard',
        gradeLevel: ['3'],
      },
    ]),
    getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', description: 'Area additive', components: LC_COMPONENTS }),
    ...overrides,
  } as unknown as KnowledgeGraphClient;
}

function makeConfig(overrides: Partial<MathStandardsAlignmentEvaluatorConfig> = {}): MathStandardsAlignmentEvaluatorConfig {
  return { anthropicApiKey: 'sk-ant-test', _kgClient: makeMockKgClient(), ...overrides };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(mockProvider.generateStructured).mockResolvedValue(MOCK_BATCH_RESPONSE);
});

// ---------------------------------------------------------------------------
// Constructor
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - constructor', () => {
  it('throws ConfigurationError when neither learningCommonsApiKey nor _kgClient provided', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant-test' })).toThrow(ConfigurationError);
  });

  it('throws ConfigurationError when anthropicApiKey is missing', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ _kgClient: makeMockKgClient() })).toThrow(ConfigurationError);
  });

  it('constructs successfully with _kgClient and anthropicApiKey', () => {
    expect(() => new MathStandardsAlignmentEvaluator(makeConfig())).not.toThrow();
  });

  it('constructs successfully with learningCommonsApiKey instead of repository', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant-test', learningCommonsApiKey: 'pk-test' })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// evaluate
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - ambiguous statement codes', () => {
  function makeLogger() {
    return { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
  }

  it('warns which standard was chosen when a code matches several', async () => {
    const logger = makeLogger();
    const repo = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockResolvedValue({
        uuid: 'uuid-abc',
        statementCode: STATEMENT_CODE,
        normalizedCode: '3.MD.C.7.D',
        description: 'Graph exponential functions',
        ambiguous: true,
        components: LC_COMPONENTS,
      }),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo, logger }));

    await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);

    expect(logger.warn).toHaveBeenCalledTimes(1);
    const [message, context] = logger.warn.mock.calls[0];
    expect(message).toContain('matched multiple standards');
    expect(context).toMatchObject({
      statementCode: STATEMENT_CODE,
      chosenUuid: 'uuid-abc',
      chosenDescription: 'Graph exponential functions',
    });
  });

  it('stays silent when the code resolves to one standard', async () => {
    const logger = makeLogger();
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ logger }));

    await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);

    expect(logger.warn).not.toHaveBeenCalled();
  });
});

describe('MathStandardsAlignmentEvaluator - evaluate', () => {
  it('returns StandardAlignmentResult with correct shape on happy path', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);

    expect(result.statementCode).toBe(STATEMENT_CODE);
    expect(result.totalCount).toBe(2);
    expect(result.alignedCount).toBe(2);
    expect(result.learningComponents).toHaveLength(2);
    for (const [i, lc] of result.learningComponents.entries()) {
      expect(lc.description).toBe(LC_COMPONENTS[i].description);
      expect(lc.aligned).toBe(true);
      expect(typeof lc.reasoning).toBe('string');
      expect(typeof lc.feedback).toBe('string');
    }
  });

  it('passes jurisdiction and academicSubject to getLearningComponentsByCode', async () => {
    const kgClient = makeMockKgClient();
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: kgClient }));
    await evaluator.evaluate(QUESTION, STATEMENT_CODE, Jurisdiction.California);

    expect(kgClient.getLearningComponentsByCode).toHaveBeenCalledWith(
      STATEMENT_CODE,
      { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics' },
    );
  });

  it('makes no LLM call and returns empty result when standard has no learning components', async () => {
    const emptyRepo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [] }) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: emptyRepo }));

    const result = await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);

    expect(result.learningComponents).toHaveLength(0);
    expect(result.alignedCount).toBe(0);
    expect(result.totalCount).toBe(0);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('throws LLMOutputProcessingError when LLM returns fewer evaluations than LCs', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [MOCK_BATCH_RESPONSE.data.evaluations[0]] }, // only lc-001, missing lc-002
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION)).rejects.toThrow(
      LLMOutputProcessingError,
    );
    await expect(evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION)).rejects.toThrow('missing verified evaluations for LC identifiers');
  });

  it('throws InputValidationError for empty question', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate('', STATEMENT_CODE, JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for question exceeding max length', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate('x'.repeat(10_001), STATEMENT_CODE, JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for empty statementCode', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate(QUESTION, '', JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('correctly handles kindergarten standard', async () => {
    const kRepo = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-k01', description: 'Count objects' }] }),
    });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-k01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: kRepo }));
    const result = await evaluator.evaluate(QUESTION, 'K.CC.A.1', JURISDICTION);
    expect(result.statementCode).toBe('K.CC.A.1');
  });

  it('alignedCount reflects actual false evaluations', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: {
        evaluations: [{ lc_id: 'lc-001', reasoning: 'Aligned', answer: 'Yes', feedback: '' }, { lc_id: 'lc-002', reasoning: 'Not aligned', answer: 'No', feedback: 'Revise to ask students to decompose' }],
      },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);
    expect(result.alignedCount).toBe(1);
    expect(result.totalCount).toBe(2);
    expect(result.learningComponents[1].aligned).toBe(false);
    expect(result.learningComponents[1].feedback).toBe('Revise to ask students to decompose');
  });
});

// ---------------------------------------------------------------------------
// evaluateItems — per-question standards (tagging validation)
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateItems (per-question codes)', () => {
  it('returns empty array for empty items list without any calls', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    expect(await evaluator.evaluateItems([], JURISDICTION)).toEqual([]);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('evaluates each item against its own standards list', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const items = [
      { question: QUESTION, statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] },
      { question: 'What is 5 × 4?', statementCodes: ['3.OA.A.1'] },
    ];
    const results = await evaluator.evaluateItems(items, JURISDICTION);

    expect(results).toHaveLength(2);
    expect(results[0].question).toBe(QUESTION);
    expect(results[0].standards).toHaveLength(2);
    expect(results[0].standards.map((s) => s.statementCode)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    expect(results[1].standards).toHaveLength(1);
  });

  it('deduplicates statementCodes per item', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: ['3.MD.C.7.d', '3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
    );

    expect(results[0].standards).toHaveLength(2);
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('onProgress fires for each completed (item, standard) pair', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const progress: Array<[number, number]> = [];
    await evaluator.evaluateItems(
      [
        { question: 'Q1', statementCodes: ['3.MD.C.7.d'] },
        { question: 'Q2', statementCodes: ['3.OA.A.1'] },
      ],
      JURISDICTION,
      { onProgress: (c, t) => progress.push([c, t]) },
    );

    expect(progress).toHaveLength(2);
    expect(progress[0][1]).toBe(2); // total = 2
    expect(progress[1][0]).toBe(2); // final completed = 2
  });
});

// ---------------------------------------------------------------------------
// evaluateItems — shared codes (cross-product / coverage analysis)
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateItems (shared codes)', () => {
  it('throws InputValidationError for empty items list', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    expect(await evaluator.evaluateItems([], JURISDICTION)).toEqual([]);
  });

  it('deduplicates shared statementCodes — each unique code evaluated once per question', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const sharedCodes = ['3.MD.C.7.d', '3.MD.C.7.d', '3.OA.A.1']; // duplicate
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: sharedCodes }],
      JURISDICTION,
    );

    expect(results[0].standards).toHaveLength(2);
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('byQuestion has correct shape for M questions × N shared codes', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const questions = ['Q1', 'Q2', 'Q3'];
    const codes = ['3.MD.C.7.d', '3.OA.A.1'];

    const results = await evaluator.evaluateItems(
      questions.map((q) => ({ question: q, statementCodes: codes })),
      JURISDICTION,
      { useCoarseFilter: false },
    );

    expect(results).toHaveLength(3);
    for (const [i, qr] of results.entries()) {
      expect(qr.question).toBe(questions[i]);
      expect(qr.standards.map((s) => s.statementCode)).toEqual(codes);
    }
  });

  it('marks coarse-filtered standards with coarseFiltered=true and empty LC list', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: '3.MD.C.7.d', relevant: true }, { standard: '3.OA.A.1', relevant: false }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const filtered = results[0].standards.find((s) => s.statementCode === '3.OA.A.1')!;
    expect(filtered.coarseFiltered).toBe(true);
    expect(filtered.learningComponents).toHaveLength(0);
    // Reported from the pre-fetch, so "skipped" is not confused with "has none".
    expect(filtered.totalCount).toBe(2);

    const evaluated = results[0].standards.find((s) => s.statementCode === '3.MD.C.7.d')!;
    expect(evaluated.coarseFiltered).toBeUndefined();
    expect(evaluated.learningComponents).toHaveLength(2);
  });

  it('does not let the coarse filter drop an ambiguous code', async () => {
    // The filter only sees one arbitrary candidate's description, so a sibling
    // candidate could be the relevant one. Filtering it out would be a false negative.
    const repo = makeMockKgClient({
      getStandardInfo: vi.fn().mockResolvedValue({
        uuid: 'uuid-abc',
        statementCode: '3.OA.A.1',
        normalizedCode: '3.OA.A.1',
        description: 'an arbitrary sibling description',
        ambiguous: true,
      }),
    });
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: '3.OA.A.1', relevant: false }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: ['3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const result = results[0].standards[0];
    expect(result.coarseFiltered).toBeUndefined();
    expect(result.learningComponents).toHaveLength(2);
  });

  it('reports the known component count on an errored pair when the pre-fetch has it', async () => {
    // Otherwise totalCount 0 would read as "this standard has no components".
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: STATEMENT_CODE, relevant: true }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockRejectedValue(new RateLimitError('rate limited', { dependency: 'anthropic' }));

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const errored = results[0].standards[0];
    expect(errored.error?.message).toContain('rate limited');
    expect(errored.alignedCount).toBe(0);
    expect(errored.totalCount).toBe(2);
  });

  it('falls back to all standards relevant when coarse filter LLM throws', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockRejectedValueOnce(new Error('coarse filter failed'))
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    expect(results[0].standards).toHaveLength(2);
    expect(results[0].standards.every((s) => !s.coarseFiltered)).toBe(true);
    expect(results[0].standards.every((s) => s.learningComponents.length > 0)).toBe(true);
  });

  it('default behaviour (useCoarseFilter=false) evaluates all pairs without a coarse filter call', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await evaluator.evaluateItems(
      [{ question: 'Q1', statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
    );
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('useCoarseFilter=true opts into coarse filter (1 coarse call + surviving detail calls)', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: '3.MD.C.7.d', relevant: true }, { standard: '3.OA.A.1', relevant: false }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await evaluator.evaluateItems(
      [{ question: 'Q1', statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );
    // 1 coarse call + 1 detail call (3.OA.A.1 was filtered) = 2 total
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('onProgress fires for each completed pair with correct counts', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const progress: Array<[number, number]> = [];
    await evaluator.evaluateItems(
      [
        { question: 'Q1', statementCodes: ['3.MD.C.7.d'] },
        { question: 'Q2', statementCodes: ['3.MD.C.7.d'] },
      ],
      JURISDICTION,
      { useCoarseFilter: false, onProgress: (c, t) => progress.push([c, t]) },
    );
    expect(progress).toHaveLength(2);
    expect(progress[0]).toEqual([1, 2]);
    expect(progress[1]).toEqual([2, 2]);
  });
});

// ---------------------------------------------------------------------------
// evaluateByGrade
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateByGrade', () => {
  it('throws InputValidationError for empty questions array', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateByGrade([], '3', JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for invalid grade', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateByGrade([QUESTION], '13', JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('fetches standards for grade and jurisdiction, deduping codes reused across courses', async () => {
    // A jurisdiction reusing one code across courses returns an item per course.
    // Without deduping, byStandard would repeat that code.
    const repo = makeMockKgClient({
      getStandardsByGrade: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', description: 'Area', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
        { caseIdentifierUUID: 'u1b', statementCode: '3.MD.C.7.d', description: 'Area, other course', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
        { caseIdentifierUUID: 'u2', statementCode: '3.OA.A.1', description: 'Products', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGrade([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });

    expect(repo.getStandardsByGrade).toHaveBeenCalledWith('3', { jurisdiction: JURISDICTION, academicSubject: 'Mathematics' });
    expect(result.byStandard.map((s) => s.statementCode)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    expect(result.byQuestion[0].standards).toHaveLength(2);
  });

  it('warns when the grade-wide fan-out is large, and stays quiet when it is not', async () => {
    const logger = { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
    const manyStandards = Array.from({ length: 501 }, (_, i) => ({
      caseIdentifierUUID: `u${i}`, statementCode: `3.XX.${i}`, description: 'd',
      statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'],
    }));

    const small = makeMockKgClient();
    await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: small, logger }))
      .evaluateByGrade([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });
    expect(logger.warn).not.toHaveBeenCalled();

    const large = makeMockKgClient({ getStandardsByGrade: vi.fn().mockResolvedValue(manyStandards) });
    await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: large, logger }))
      .evaluateByGrade([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });

    expect(logger.warn).toHaveBeenCalledTimes(1);
    expect(logger.warn.mock.calls[0][1]).toMatchObject({ questions: 1, standards: 501, pairs: 501 });
  });

  it('returns byStandard with coverageCount counting questions with alignedCount > 0', async () => {
    let callNum = 0;
    vi.mocked(mockProvider.generateStructured).mockImplementation(async () => {
      callNum++;
      const answer = callNum === 1 ? 'Yes' : 'No';
      return {
        ...MOCK_BATCH_RESPONSE,
        data: {
          evaluations: [
            { lc_id: 'lc-001', reasoning: 'r', answer, feedback: '' },
            { lc_id: 'lc-002', reasoning: 'r', answer, feedback: '' },
          ],
        },
      };
    });

    const repo = makeMockKgClient({
      getStandardsByGrade: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: STATEMENT_CODE, description: 'Area', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGrade(['Q1', 'Q2'], '3', JURISDICTION, { useCoarseFilter: false });

    expect(result.byStandard[0].coverageCount).toBe(1);
    expect(result.byStandard[0].coveredBy[0].question).toBe('Q1');
  });

  it('returns empty byStandard and byQuestion stubs when KG returns no standards for grade', async () => {
    const repo = makeMockKgClient({ getStandardsByGrade: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGrade([QUESTION], '3', JURISDICTION);
    expect(result.byStandard).toEqual([]);
    expect(result.byQuestion).toEqual([{ question: QUESTION, standards: [] }]);
  });

  it('passes California jurisdiction to getStandardsByGrade', async () => {
    const repo = makeMockKgClient({ getStandardsByGrade: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    await evaluator.evaluateByGrade([QUESTION], '5', Jurisdiction.California);

    expect(repo.getStandardsByGrade).toHaveBeenCalledWith('5', { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics' });
  });
});

// ---------------------------------------------------------------------------
// Error isolation
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateItems error isolation', () => {
  function failingCodeClient(badCode: string): KnowledgeGraphClient {
    return makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockImplementation((code: string) =>
        code === badCode
          ? Promise.reject(new KnowledgeGraphError(`Standard not found: "${badCode}"`))
          : Promise.resolve({ uuid: 'uuid-abc', description: 'Area additive', components: LC_COMPONENTS }),
      ),
    });
  }

  it('isolates a failing standard without discarding its siblings', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: failingCodeClient('BAD.CODE') }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE, 'BAD.CODE'] }],
      JURISDICTION,
    );

    expect(results).toHaveLength(1);
    const [good, bad] = results[0].standards;
    expect(good.error).toBeUndefined();
    expect(good.alignedCount).toBe(2);
    expect(bad.error?.message).toContain('Standard not found');
  });

  it('attributes the error to the correct statementCode and carries a machine-readable code', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: failingCodeClient('BAD.CODE') }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE, 'BAD.CODE'] }],
      JURISDICTION,
    );

    const errored = results[0].standards.filter((s) => s.error);
    expect(errored).toHaveLength(1);
    expect(errored[0].statementCode).toBe('BAD.CODE');
    // A report needs to group failures by kind, not by message text.
    expect(errored[0].error?.name).toBe('KnowledgeGraphError');
  });

  it('carries statusCode and retryable through so a report can separate transient failures', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(new RateLimitError('slow down', { dependency: 'anthropic' }));
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE] }],
      JURISDICTION,
    );

    expect(results[0].standards[0].error).toMatchObject({
      name: 'RateLimitError',
      statusCode: 429,
      retryable: true,
    });
  });

  it('does not discard other items when one item fails entirely', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: failingCodeClient('BAD.CODE') }));

    const results = await evaluator.evaluateItems(
      [
        { question: 'Q1', statementCodes: ['BAD.CODE'] },
        { question: 'Q2', statementCodes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
    );

    expect(results).toHaveLength(2);
    expect(results[0].standards[0].error).toBeDefined();
    expect(results[1].standards[0].error).toBeUndefined();
    expect(results[1].standards[0].alignedCount).toBe(2);
  });

  it('surfaces an LLM failure as a per-pair error rather than rejecting', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(
      new RateLimitError('rate limited', { dependency: 'anthropic' }),
    );
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE] }],
      JURISDICTION,
    );

    expect(results[0].standards[0].error?.message).toContain('rate limited');
    expect(results[0].standards[0].alignedCount).toBe(0);
  });

  it('a throwing progress callback cannot corrupt results, counts, or the batch', async () => {
    const logger = { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
    const onProgress = vi.fn(() => { throw new Error('progress bar blew up'); });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ logger }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE, 'OTHER.CODE'] }],
      JURISDICTION,
      { onProgress },
    );

    // Successful pairs stay successful, each pair is counted once, nothing rejects.
    expect(results[0].standards.every((s) => s.error === undefined)).toBe(true);
    expect(results[0].standards.every((s) => s.alignedCount === 2)).toBe(true);
    expect(onProgress).toHaveBeenCalledTimes(2);
    expect(onProgress).toHaveBeenLastCalledWith(2, 2);
    expect(logger.warn).toHaveBeenCalledTimes(2);
  });

  it('reports progress for failed pairs too, so totals reconcile', async () => {
    const repo = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockRejectedValue(new KnowledgeGraphError('nope')),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const onProgress = vi.fn();

    await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE, 'OTHER.CODE'] }],
      JURISDICTION,
      { onProgress },
    );

    expect(onProgress).toHaveBeenCalledTimes(2);
    expect(onProgress).toHaveBeenLastCalledWith(2, 2);
  });

  it('evaluate() still throws for a single pair', async () => {
    const repo = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockRejectedValue(new KnowledgeGraphError('nope')),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    await expect(evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION)).rejects.toThrow();
  });

  it('isolates a validation failure to the offending item', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [
        { question: '', statementCodes: [STATEMENT_CODE] },
        { question: QUESTION, statementCodes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
    );

    expect(results).toHaveLength(2);
    // Same shape as every other failure, so grouping by name does not miss these.
    expect(results[0].standards[0].error?.name).toBe('InputValidationError');
    expect(results[0].standards[0].statementCode).toBe(STATEMENT_CODE);
    expect(results[1].standards[0].error).toBeUndefined();
    expect(results[1].standards[0].alignedCount).toBe(2);
  });

  it('surfaces a validation failure even when the item has no statement codes', async () => {
    // Nothing to map over, so without an item-level error the failure vanishes.
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: '', statementCodes: [] }],
      JURISDICTION,
    );

    expect(results).toHaveLength(1);
    expect(results[0].standards).toEqual([]);
    expect(results[0].error).toMatchObject({ name: 'InputValidationError' });
  });

  it('excludes an invalid item from the progress denominator', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const onProgress = vi.fn();

    await evaluator.evaluateItems(
      [
        { question: '', statementCodes: [STATEMENT_CODE] },
        { question: QUESTION, statementCodes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
      { onProgress },
    );

    expect(onProgress).toHaveBeenLastCalledWith(1, 1);
  });

  it('distinguishes zero coverage caused by errors from genuine non-alignment', async () => {
    const repo = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockRejectedValue(new KnowledgeGraphError('nope')),
    });
    const errored = await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }))
      .evaluateByGrade(['Q1'], '3', JURISDICTION);

    expect(errored.byQuestion[0].standards[0].error).toBeDefined();
    expect(errored.byStandard[0].coveredBy).toEqual([]);
    expect(errored.byStandard[0]).toMatchObject({
      coverageCount: 0, errorCount: 1, evaluatedCount: 0, noComponentsCount: 0,
    });

    // Same zero coverage, but measured: every LC came back unaligned.
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: {
        evaluations: MOCK_BATCH_RESPONSE.data.evaluations.map((e) => ({ ...e, answer: 'No' })),
      },
    });
    const unaligned = await new MathStandardsAlignmentEvaluator(makeConfig())
      .evaluateByGrade(['Q1'], '3', JURISDICTION);

    expect(unaligned.byStandard[0]).toMatchObject({
      coverageCount: 0, errorCount: 0, evaluatedCount: 1, noComponentsCount: 0,
    });

    // Third way to reach zero coverage: never evaluated because the filter skipped it.
    vi.mocked(mockProvider.generateStructured).mockReset();
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: { standards: [{ standard: STATEMENT_CODE, relevant: false }] },
      model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
    });
    const filtered = await new MathStandardsAlignmentEvaluator(makeConfig())
      .evaluateByGrade(['Q1'], '3', JURISDICTION, { useCoarseFilter: true });

    expect(filtered.byStandard[0]).toMatchObject({
      coverageCount: 0, errorCount: 0, evaluatedCount: 0, filteredCount: 1,
    });

    // Fourth way: the standard exists but has no learning components, so nothing was
    // measured. Counting it as evaluated would read as a judgement.
    const noComponents = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [] }),
    });
    const unauthored = await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: noComponents }))
      .evaluateByGrade(['Q1'], '3', JURISDICTION);

    // Its own counter, so all-zeros is never the only signal.
    expect(unauthored.byStandard[0]).toMatchObject({
      coverageCount: 0, errorCount: 0, evaluatedCount: 0, filteredCount: 0, noComponentsCount: 1,
    });
  });
});

describe('MathStandardsAlignmentEvaluator - shared concurrency', () => {
  it('shares one LLM concurrency budget across concurrent evaluateItems calls', async () => {
    let inFlight = 0;
    let peak = 0;
    vi.mocked(mockProvider.generateStructured).mockImplementation(async () => {
      inFlight++;
      peak = Math.max(peak, inFlight);
      await new Promise((resolve) => setTimeout(resolve, 5));
      inFlight--;
      return MOCK_BATCH_RESPONSE;
    });

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ concurrency: 2 }));
    const items = (prefix: string) =>
      Array.from({ length: 4 }, (_, i) => ({ question: `${prefix}-${i}`, statementCodes: [STATEMENT_CODE] }));

    await Promise.all([
      evaluator.evaluateItems(items('A'), JURISDICTION),
      evaluator.evaluateItems(items('B'), JURISDICTION),
    ]);

    // Exact: a per-call limiter would peak at 4, and "<= 2" alone would pass
    // vacuously if everything serialized.
    expect(peak).toBe(2);
  });
});
