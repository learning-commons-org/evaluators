import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
  type MathStandardsAlignmentEvaluatorConfig,
} from '../../../../src/evaluators/math/standards-alignment.js';
import { ConfigurationError, ValidationError, APIError } from '../../../../src/errors.js';
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

const GRADE = '3';
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
        gradeLevel: [GRADE],
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
  it('throws ConfigurationError when neither platformApiKey nor _kgClient provided', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant-test' })).toThrow(ConfigurationError);
  });

  it('throws ConfigurationError when anthropicApiKey is missing', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ _kgClient: makeMockKgClient() })).toThrow(ConfigurationError);
  });

  it('constructs successfully with _kgClient and anthropicApiKey', () => {
    expect(() => new MathStandardsAlignmentEvaluator(makeConfig())).not.toThrow();
  });

  it('constructs successfully with platformApiKey instead of repository', () => {
    expect(() => new MathStandardsAlignmentEvaluator({ anthropicApiKey: 'sk-ant-test', platformApiKey: 'pk-test' })).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// evaluate
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluate', () => {
  it('returns StandardAlignmentResult with correct shape on happy path', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION);

    expect(result.statementCode).toBe(STATEMENT_CODE);
    expect(result.grade).toBeUndefined();
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
      { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics', limit: 1 },
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

  it('throws APIError when LLM returns fewer evaluations than LCs', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [MOCK_BATCH_RESPONSE.data.evaluations[0]] }, // only lc-001, missing lc-002
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION)).rejects.toThrow(APIError);
    await expect(evaluator.evaluate(QUESTION, STATEMENT_CODE, JURISDICTION)).rejects.toThrow('missing verified evaluations for LC identifiers');
  });

  it('throws ValidationError for empty question', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate('', STATEMENT_CODE, JURISDICTION)).rejects.toThrow(ValidationError);
  });

  it('throws ValidationError for question exceeding max length', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate('x'.repeat(10_001), STATEMENT_CODE, JURISDICTION)).rejects.toThrow(ValidationError);
  });

  it('throws ValidationError for empty statementCode', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate(QUESTION, '', JURISDICTION)).rejects.toThrow(ValidationError);
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
    expect(result.grade).toBeUndefined();
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
// evaluateItems
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateItems', () => {
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
      { question: QUESTION, grade: '3', statementCodes: ['3.MD.C.7.d', '3.OA.A.1'] },
      { question: 'What is 5 × 4?', grade: '3', statementCodes: ['3.OA.A.1'] },
    ];
    const results = await evaluator.evaluateItems(items, JURISDICTION);

    expect(results).toHaveLength(2);
    expect(results[0].question).toBe(QUESTION);
    expect(results[0].standards).toHaveLength(2);
    expect(results[0].standards.map((s) => s.statementCode)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    expect(results[1].standards).toHaveLength(1);
  });

  it('supports items with different grades', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const items = [
      { question: 'Grade 3 question', grade: '3', statementCodes: ['3.OA.A.1'] },
      { question: 'Grade 5 question', grade: '5', statementCodes: ['5.NBT.A.1'] },
    ];
    const results = await evaluator.evaluateItems(items, JURISDICTION);
    expect(results[0].grade).toBe('3');
    expect(results[1].grade).toBe('5');
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
        { question: 'Q1', grade: '3', statementCodes: ['3.MD.C.7.d'] },
        { question: 'Q2', grade: '3', statementCodes: ['3.OA.A.1'] },
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
// evaluateQuestionBank
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateQuestionBank', () => {
  it('throws ValidationError for empty questions array', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateQuestionBank([], ['3.MD.C.7.d'], JURISDICTION)).rejects.toThrow(ValidationError);
  });

  it('throws ValidationError for empty statementCodes array', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateQuestionBank([{ question: QUESTION, grade: GRADE }], [], JURISDICTION)).rejects.toThrow(ValidationError);
  });

  it('deduplicates statementCodes — evaluate called once per unique code regardless of duplicates in input', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const result = await evaluator.evaluateQuestionBank(
      [{ question: QUESTION, grade: GRADE }],
      ['3.MD.C.7.d', '3.MD.C.7.d', '3.OA.A.1'],  // 3.MD.C.7.d duplicated
      JURISDICTION,
      { useCoarseFilter: false },
    );

    // byStandard should have 2 unique entries, not 3
    expect(result.byStandard).toHaveLength(2);
    expect(result.byStandard.map((s) => s.statementCode)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    // byQuestion should also have 2 standard results, not 3
    expect(result.byQuestion[0].standards).toHaveLength(2);
    // LLM called twice (once per unique standard), not 3 times
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('onProgress total reflects unique standards, not raw input length with duplicates', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const progress: Array<[number, number]> = [];

    await evaluator.evaluateQuestionBank(
      [{ question: QUESTION, grade: GRADE }],
      ['3.MD.C.7.d', '3.MD.C.7.d'],  // same code twice
      JURISDICTION,
      { useCoarseFilter: false, onProgress: (c, t) => progress.push([c, t]) },
    );

    // total should be 1 (one unique standard), completed should never exceed 1
    expect(progress).toHaveLength(1);
    expect(progress[0]).toEqual([1, 1]);
  });

  it('byQuestion and byStandard have correct shape and codes for M×N', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const questionItems = [
      { question: 'Q1', grade: '3' },
      { question: 'Q2', grade: '3' },
      { question: 'Q3', grade: '3' },
    ];
    const statementCodes = ['3.MD.C.7.d', '3.OA.A.1'];

    const result = await evaluator.evaluateQuestionBank(questionItems, statementCodes, JURISDICTION, { useCoarseFilter: false });

    expect(result.byQuestion).toHaveLength(3);
    for (const [i, qr] of result.byQuestion.entries()) {
      expect(qr.question).toBe(questionItems[i].question);
      expect(qr.grade).toBe('3');
      expect(qr.standards.map((s) => s.statementCode)).toEqual(statementCodes);
    }
    expect(result.byStandard).toHaveLength(2);
    expect(result.byStandard.map((s) => s.statementCode)).toEqual(statementCodes);
  });

  it('marks coarse-filtered standards with coarseFiltered=true and empty LC list', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: '3.MD.C.7.d', relevant: true }, { standard: '3.OA.A.1', relevant: false }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluateQuestionBank([{ question: QUESTION, grade: GRADE }], ['3.MD.C.7.d', '3.OA.A.1'], JURISDICTION, { useCoarseFilter: true });

    const filtered = result.byQuestion[0].standards.find((s) => s.statementCode === '3.OA.A.1')!;
    expect(filtered.coarseFiltered).toBe(true);
    expect(filtered.learningComponents).toHaveLength(0);

    const evaluated = result.byQuestion[0].standards.find((s) => s.statementCode === '3.MD.C.7.d')!;
    expect(evaluated.coarseFiltered).toBeUndefined();
    expect(evaluated.learningComponents).toHaveLength(2);
  });

  it('falls back to all standards relevant when coarse filter LLM throws', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockRejectedValueOnce(new Error('coarse filter failed'))
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluateQuestionBank([{ question: QUESTION, grade: GRADE }], ['3.MD.C.7.d', '3.OA.A.1'], JURISDICTION, { useCoarseFilter: true });

    expect(result.byQuestion[0].standards).toHaveLength(2);
    expect(result.byQuestion[0].standards.every((s) => !s.coarseFiltered)).toBe(true);
    expect(result.byQuestion[0].standards.every((s) => s.learningComponents.length > 0)).toBe(true);
  });

  it('default behaviour (useCoarseFilter=false) evaluates all pairs without a coarse filter call', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await evaluator.evaluateQuestionBank(
      [{ question: 'Q1', grade: '3' }],
      ['3.MD.C.7.d', '3.OA.A.1'],
      JURISDICTION,
    );
    // Default is useCoarseFilter=false: exactly 2 detail LLM calls, no coarse call
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
    await evaluator.evaluateQuestionBank(
      [{ question: 'Q1', grade: '3' }],
      ['3.MD.C.7.d', '3.OA.A.1'],
      JURISDICTION,
      { useCoarseFilter: true },
    );
    // 1 coarse call + 1 detail call (3.OA.A.1 was filtered) = 2 total
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('onProgress fires for each completed pair with correct counts', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const progress: Array<[number, number]> = [];
    await evaluator.evaluateQuestionBank(
      [{ question: 'Q1', grade: '3' }, { question: 'Q2', grade: '3' }],
      ['3.MD.C.7.d'],
      JURISDICTION,
      { useCoarseFilter: false, onProgress: (c, t) => progress.push([c, t]) },
    );
    expect(progress).toHaveLength(2);
    expect(progress[0][0]).toBe(1);
    expect(progress[0][1]).toBe(2);
    expect(progress[1][0]).toBe(2);
    expect(progress[1][1]).toBe(2);
  });

  it('byStandard.coverageCount counts questions with alignedCount > 0', async () => {
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

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const result = await evaluator.evaluateQuestionBank(
      [{ question: 'Q1', grade: '3' }, { question: 'Q2', grade: '3' }],
      [STATEMENT_CODE],
      JURISDICTION,
      { useCoarseFilter: false },
    );

    expect(result.byStandard[0].coverageCount).toBe(1);
    expect(result.byStandard[0].coveredBy[0].question).toBe('Q1');
  });
});

// ---------------------------------------------------------------------------
// evaluateByGrade
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateByGrade', () => {
  it('throws ValidationError for invalid grade', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateByGrade([QUESTION], '13', JURISDICTION)).rejects.toThrow(ValidationError);
  });

  it('fetches standards for grade and jurisdiction and runs M×N evaluation', async () => {
    const repo = makeMockKgClient({
      getStandardsByGrade: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', description: 'Area', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
        { caseIdentifierUUID: 'u2', statementCode: '3.OA.A.1', description: 'Products', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGrade([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });

    expect(repo.getStandardsByGrade).toHaveBeenCalledWith('3', { jurisdiction: JURISDICTION, academicSubject: 'Mathematics' });
    expect(result.byStandard).toHaveLength(2);
    expect(result.byQuestion[0].standards).toHaveLength(2);
  });

  it('accepts plain string array for questions', async () => {
    const repo = makeMockKgClient({ getStandardsByGrade: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGrade([QUESTION], '3', JURISDICTION);
    expect(result.byStandard).toEqual([]);
  });

  it('passes California jurisdiction to getStandardsByGrade', async () => {
    const repo = makeMockKgClient({ getStandardsByGrade: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    await evaluator.evaluateByGrade([QUESTION], '5', Jurisdiction.California);

    expect(repo.getStandardsByGrade).toHaveBeenCalledWith('5', { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics' });
  });
});
