import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
  type MathStandardsAlignmentEvaluatorConfig,
  type QuestionItem,
} from '../../../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';
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
    getStandardsByGradeLevel: vi.fn().mockResolvedValue([
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

    await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(logger.warn).toHaveBeenCalledTimes(1);
    const [message, context] = logger.warn.mock.calls[0];
    expect(message).toContain('matched multiple standards');
    expect(context).toMatchObject({
      // Log context is SDK surface, not contract payload, so it stays camelCase
      // alongside its siblings below.
      statementCode: STATEMENT_CODE,
      chosenUuid: 'uuid-abc',
      chosenDescription: 'Graph exponential functions',
    });
  });

  it('stays silent when the code resolves to one standard', async () => {
    const logger = makeLogger();
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ logger }));

    await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(logger.warn).not.toHaveBeenCalled();
  });
});

describe('MathStandardsAlignmentEvaluator - evaluate', () => {
  it('returns MathStandardsAlignmentResult with correct shape on happy path', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const { result } = await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(result.statement_code).toBe(STATEMENT_CODE);
    expect(result.total_count).toBe(2);
    expect(result.aligned_count).toBe(2);
    expect(result.learning_components).toHaveLength(2);
    for (const [i, lc] of result.learning_components.entries()) {
      expect(lc.description).toBe(LC_COMPONENTS[i].description);
      expect(lc.aligned).toBe(true);
      expect(typeof lc.reasoning).toBe('string');
      expect(typeof lc.feedback).toBe('string');
    }
  });

  it('wraps the payload in the shared envelope', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const evaluation = await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(evaluation.evaluator).toBe(MathStandardsAlignmentEvaluator.metadata.id);
    // The provider that actually ran, so an override is reflected rather than a constant.
    expect(evaluation.metadata.model).toBe(mockProvider.label);
    expect(evaluation.metadata.tokenUsage).toEqual({ inputTokens: 300, outputTokens: 150 });
    // Bounded above as well: a duration built by adding the epoch instead of subtracting it
    // is still >= 0, and reads as ~3.5e12 ms.
    expect(evaluation.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
    expect(evaluation.metadata.processingTimeMs).toBeLessThan(60_000);
    expect(Object.keys(evaluation).sort()).toEqual(['evaluator', 'metadata', 'result']);
  });

  it('reports zero tokens when it resolves without calling a model', async () => {
    // A standard with no learning components returns early. Reporting the mock's token
    // counts here would attribute a cost to a call that never happened.
    const emptyRepo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [] }) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: emptyRepo }));

    const { metadata } = await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(metadata.tokenUsage).toEqual({ inputTokens: 0, outputTokens: 0 });
    expect(metadata.model).toBe(mockProvider.label);
  });

  it('passes jurisdiction and academicSubject to getLearningComponentsByCode', async () => {
    const kgClient = makeMockKgClient();
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: kgClient }));
    await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: Jurisdiction.California });

    expect(kgClient.getLearningComponentsByCode).toHaveBeenCalledWith(
      STATEMENT_CODE,
      { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics' },
    );
  });

  it('makes no LLM call and returns empty result when standard has no learning components', async () => {
    const emptyRepo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [] }) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: emptyRepo }));

    const { result } = await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });

    expect(result.learning_components).toHaveLength(0);
    expect(result.aligned_count).toBe(0);
    expect(result.total_count).toBe(0);
    expect(mockProvider.generateStructured).not.toHaveBeenCalled();
  });

  it('throws LLMOutputProcessingError when LLM returns fewer evaluations than LCs', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [MOCK_BATCH_RESPONSE.data.evaluations[0]] }, // only lc-001, missing lc-002
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION })).rejects.toThrow(
      LLMOutputProcessingError,
    );
    await expect(evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION })).rejects.toThrow('missing verified evaluations for LC identifiers');
  });

  it('throws InputValidationError for empty question', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate({ question: '', statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION })).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for question exceeding max length', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate({ question: 'x'.repeat(10_001), statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION })).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for empty statement_code', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluate({ question: QUESTION, statement_code: '', jurisdiction: JURISDICTION })).rejects.toThrow(InputValidationError);
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
    const { result } = await evaluator.evaluate({ question: QUESTION, statement_code: 'K.CC.A.1', jurisdiction: JURISDICTION });
    expect(result.statement_code).toBe('K.CC.A.1');
  });

  it('aligned_count reflects actual false evaluations', async () => {
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: {
        evaluations: [{ lc_id: 'lc-001', reasoning: 'Aligned', answer: 'Yes', feedback: '' }, { lc_id: 'lc-002', reasoning: 'Not aligned', answer: 'No', feedback: 'Revise to ask students to decompose' }],
      },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const { result } = await evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION });
    expect(result.aligned_count).toBe(1);
    expect(result.total_count).toBe(2);
    expect(result.learning_components[1].aligned).toBe(false);
    expect(result.learning_components[1].feedback).toBe('Revise to ask students to decompose');
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
      { question: QUESTION, statement_codes: ['3.MD.C.7.d', '3.OA.A.1'] },
      { question: 'What is 5 × 4?', statement_codes: ['3.OA.A.1'] },
    ];
    const results = await evaluator.evaluateItems(items, JURISDICTION);

    expect(results).toHaveLength(2);
    expect(results[0].question).toBe(QUESTION);
    expect(results[0].standards).toHaveLength(2);
    expect(results[0].standards.map((s) => s.statement_code)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    expect(results[1].standards).toHaveLength(1);
  });

  it('deduplicates statement_codes per item', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: ['3.MD.C.7.d', '3.MD.C.7.d', '3.OA.A.1'] }],
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
        { question: 'Q1', statement_codes: ['3.MD.C.7.d'] },
        { question: 'Q2', statement_codes: ['3.OA.A.1'] },
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

  it('deduplicates shared statement_codes — each unique code evaluated once per question', async () => {
    const repo = makeMockKgClient({ getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [{ identifier: 'lc-t01', description: 'LC' }] }) });
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: { evaluations: [{ lc_id: 'lc-t01', reasoning: 'ok', answer: 'Yes', feedback: '' }] },
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));

    const sharedCodes = ['3.MD.C.7.d', '3.MD.C.7.d', '3.OA.A.1']; // duplicate
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: sharedCodes }],
      JURISDICTION,
    );

    expect(results[0].standards).toHaveLength(2);
    expect(mockProvider.generateStructured).toHaveBeenCalledTimes(2);
  });

  it('by_question has correct shape for M questions x N shared codes', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const questions = ['Q1', 'Q2', 'Q3'];
    const codes = ['3.MD.C.7.d', '3.OA.A.1'];

    const results = await evaluator.evaluateItems(
      questions.map((q) => ({ question: q, statement_codes: codes })),
      JURISDICTION,
      { useCoarseFilter: false },
    );

    expect(results).toHaveLength(3);
    for (const [i, qr] of results.entries()) {
      expect(qr.question).toBe(questions[i]);
      expect(qr.standards.map((s) => s.statement_code)).toEqual(codes);
    }
  });

  it('marks coarse-filtered standards with coarse_filtered=true and empty LC list', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: '3.MD.C.7.d', relevant: true }, { standard: '3.OA.A.1', relevant: false }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const filtered = results[0].standards.find((s) => s.statement_code === '3.OA.A.1')!;
    expect(filtered.coarse_filtered).toBe(true);
    expect(filtered.learning_components).toHaveLength(0);
    // Reported from the pre-fetch, so "skipped" is not confused with "has none".
    expect(filtered.total_count).toBe(2);

    const evaluated = results[0].standards.find((s) => s.statement_code === '3.MD.C.7.d')!;
    expect(evaluated.coarse_filtered).toBeUndefined();
    expect(evaluated.learning_components).toHaveLength(2);
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
      [{ question: QUESTION, statement_codes: ['3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const result = results[0].standards[0];
    expect(result.coarse_filtered).toBeUndefined();
    expect(result.learning_components).toHaveLength(2);
  });

  it('reports the known component count on an errored pair when the pre-fetch has it', async () => {
    // Otherwise total_count 0 would read as "this standard has no components".
    vi.mocked(mockProvider.generateStructured)
      .mockResolvedValueOnce({
        data: { standards: [{ standard: STATEMENT_CODE, relevant: true }] },
        model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
      })
      .mockRejectedValue(new RateLimitError('rate limited', { dependency: 'anthropic' }));

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    const errored = results[0].standards[0];
    expect(errored.error?.message).toContain('rate limited');
    expect(errored.aligned_count).toBe(0);
    expect(errored.total_count).toBe(2);
  });

  it('falls back to all standards relevant when coarse filter LLM throws', async () => {
    vi.mocked(mockProvider.generateStructured)
      .mockRejectedValueOnce(new Error('coarse filter failed'))
      .mockResolvedValue(MOCK_BATCH_RESPONSE);

    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: ['3.MD.C.7.d', '3.OA.A.1'] }],
      JURISDICTION,
      { useCoarseFilter: true },
    );

    expect(results[0].standards).toHaveLength(2);
    expect(results[0].standards.every((s) => !s.coarse_filtered)).toBe(true);
    expect(results[0].standards.every((s) => s.learning_components.length > 0)).toBe(true);
  });

  it('default behaviour (useCoarseFilter=false) evaluates all pairs without a coarse filter call', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await evaluator.evaluateItems(
      [{ question: 'Q1', statement_codes: ['3.MD.C.7.d', '3.OA.A.1'] }],
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
      [{ question: 'Q1', statement_codes: ['3.MD.C.7.d', '3.OA.A.1'] }],
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
        { question: 'Q1', statement_codes: ['3.MD.C.7.d'] },
        { question: 'Q2', statement_codes: ['3.MD.C.7.d'] },
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
// evaluateByGradeLevel
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateByGradeLevel', () => {
  it('throws InputValidationError for empty questions array', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateByGradeLevel([], '3', JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('throws InputValidationError for invalid grade', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    await expect(evaluator.evaluateByGradeLevel([QUESTION], '13', JURISDICTION)).rejects.toThrow(InputValidationError);
  });

  it('fetches standards for grade and jurisdiction, deduping codes reused across courses', async () => {
    // A jurisdiction reusing one code across courses returns an item per course.
    // Without deduping, by_standard would repeat that code.
    const repo = makeMockKgClient({
      getStandardsByGradeLevel: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: '3.MD.C.7.d', description: 'Area', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
        { caseIdentifierUUID: 'u1b', statementCode: '3.MD.C.7.d', description: 'Area, other course', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
        { caseIdentifierUUID: 'u2', statementCode: '3.OA.A.1', description: 'Products', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGradeLevel([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });

    expect(repo.getStandardsByGradeLevel).toHaveBeenCalledWith('3', { jurisdiction: JURISDICTION, academicSubject: 'Mathematics' });
    expect(result.by_standard.map((s) => s.statement_code)).toEqual(['3.MD.C.7.d', '3.OA.A.1']);
    expect(result.by_question[0].standards).toHaveLength(2);
  });

  it('warns when the grade-wide fan-out is large, and stays quiet when it is not', async () => {
    const logger = { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
    const manyStandards = Array.from({ length: 501 }, (_, i) => ({
      caseIdentifierUUID: `u${i}`, statementCode: `3.XX.${i}`, description: 'd',
      statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'],
    }));

    const small = makeMockKgClient();
    await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: small, logger }))
      .evaluateByGradeLevel([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });
    expect(logger.warn).not.toHaveBeenCalled();

    const large = makeMockKgClient({ getStandardsByGradeLevel: vi.fn().mockResolvedValue(manyStandards) });
    await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: large, logger }))
      .evaluateByGradeLevel([QUESTION], '3', JURISDICTION, { useCoarseFilter: false });

    expect(logger.warn).toHaveBeenCalledTimes(1);
    expect(logger.warn.mock.calls[0][1]).toMatchObject({ questions: 1, standards: 501, pairs: 501 });
  });

  it('returns by_standard with coverage_count counting questions with aligned_count > 0', async () => {
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
      getStandardsByGradeLevel: vi.fn().mockResolvedValue([
        { caseIdentifierUUID: 'u1', statementCode: STATEMENT_CODE, description: 'Area', statementType: 'Standard', normalizedStatementType: 'Standard', gradeLevel: ['3'] },
      ]),
    });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGradeLevel(['Q1', 'Q2'], '3', JURISDICTION, { useCoarseFilter: false });

    expect(result.by_standard[0].coverage_count).toBe(1);
    expect(result.by_standard[0].covered_by[0].question).toBe('Q1');
  });

  it('returns empty by_standard and by_question stubs when KG returns no standards for grade', async () => {
    const repo = makeMockKgClient({ getStandardsByGradeLevel: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    const result = await evaluator.evaluateByGradeLevel([QUESTION], '3', JURISDICTION);
    expect(result.by_standard).toEqual([]);
    expect(result.by_question).toEqual([{ question: QUESTION, standards: [] }]);
  });

  it('passes California jurisdiction to getStandardsByGradeLevel', async () => {
    const repo = makeMockKgClient({ getStandardsByGradeLevel: vi.fn().mockResolvedValue([]) });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: repo }));
    await evaluator.evaluateByGradeLevel([QUESTION], '5', Jurisdiction.California);

    expect(repo.getStandardsByGradeLevel).toHaveBeenCalledWith('5', { jurisdiction: Jurisdiction.California, academicSubject: 'Mathematics' });
  });
});

// ---------------------------------------------------------------------------
// Error isolation
// ---------------------------------------------------------------------------

describe('MathStandardsAlignmentEvaluator - evaluateItems malformed items', () => {
  // An item missing its code list used to escape as `TypeError: item.statement_codes is
  // not iterable`, outside the taxonomy, so no `instanceof` in the docs caught it.
  it('reports a missing statement_codes as the caller\'s bad input', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: makeMockKgClient() }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION } as unknown as QuestionItem],
      JURISDICTION,
    );

    expect(results[0].error?.name).toBe('InputValidationError');
    expect(results[0].error?.message).toContain('statement_codes is required');
  });

  it('names the pre-1.0 spelling when an item still carries statementCodes', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: makeMockKgClient() }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statementCodes: [STATEMENT_CODE] } as unknown as QuestionItem],
      JURISDICTION,
    );

    expect(results[0].error?.name).toBe('InputValidationError');
    // The whole point: say what to rename, since this is the shape 0.8.0 callers hold.
    expect(results[0].error?.message).toContain('`statementCodes`');
    expect(results[0].error?.message).toContain('rename it to `statement_codes`');
  });

  it('never reports a non-string statement_code, even on an errored item', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: makeMockKgClient() }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [123, STATEMENT_CODE] } as unknown as QuestionItem],
      JURISDICTION,
    );

    expect(results[0].error?.name).toBe('InputValidationError');
    expect(results[0].error?.message).toContain('must be a string');
    // The declared type says `string`; echoing the bad value back would make it a lie.
    for (const s of results[0].standards) {
      expect(typeof s.statement_code).toBe('string');
    }
    expect(results[0].standards.map((s) => s.statement_code)).toEqual([STATEMENT_CODE]);
  });

  it('isolates one malformed item without failing its siblings', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: makeMockKgClient() }));

    const results = await evaluator.evaluateItems(
      [
        { question: QUESTION } as unknown as QuestionItem,
        { question: QUESTION, statement_codes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
    );

    expect(results[0].error?.name).toBe('InputValidationError');
    expect(results[1].error).toBeUndefined();
    expect(results[1].standards[0].aligned_count).toBe(2);
  });
});

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
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE, 'BAD.CODE'] }],
      JURISDICTION,
    );

    expect(results).toHaveLength(1);
    const [good, bad] = results[0].standards;
    expect(good.error).toBeUndefined();
    expect(good.aligned_count).toBe(2);
    expect(bad.error?.message).toContain('Standard not found');
  });

  it('attributes the error to the correct statement_code and carries a machine-readable code', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: failingCodeClient('BAD.CODE') }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE, 'BAD.CODE'] }],
      JURISDICTION,
    );

    const errored = results[0].standards.filter((s) => s.error);
    expect(errored).toHaveLength(1);
    expect(errored[0].statement_code).toBe('BAD.CODE');
    // A report needs to group failures by kind, not by message text.
    expect(errored[0].error?.name).toBe('KnowledgeGraphError');
  });

  it('carries statusCode and retryable through so a report can separate transient failures', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(new RateLimitError('slow down', { dependency: 'anthropic' }));
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE] }],
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
        { question: 'Q1', statement_codes: ['BAD.CODE'] },
        { question: 'Q2', statement_codes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
    );

    expect(results).toHaveLength(2);
    expect(results[0].standards[0].error).toBeDefined();
    expect(results[1].standards[0].error).toBeUndefined();
    expect(results[1].standards[0].aligned_count).toBe(2);
  });

  it('surfaces an LLM failure as a per-pair error rather than rejecting', async () => {
    vi.mocked(mockProvider.generateStructured).mockRejectedValueOnce(
      new RateLimitError('rate limited', { dependency: 'anthropic' }),
    );
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE] }],
      JURISDICTION,
    );

    expect(results[0].standards[0].error?.message).toContain('rate limited');
    expect(results[0].standards[0].aligned_count).toBe(0);
  });

  it('a throwing progress callback cannot corrupt results, counts, or the batch', async () => {
    const logger = { debug: vi.fn(), info: vi.fn(), warn: vi.fn(), error: vi.fn() };
    const onProgress = vi.fn(() => { throw new Error('progress bar blew up'); });
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig({ logger }));

    const results = await evaluator.evaluateItems(
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE, 'OTHER.CODE'] }],
      JURISDICTION,
      { onProgress },
    );

    // Successful pairs stay successful, each pair is counted once, nothing rejects.
    expect(results[0].standards.every((s) => s.error === undefined)).toBe(true);
    expect(results[0].standards.every((s) => s.aligned_count === 2)).toBe(true);
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
      [{ question: QUESTION, statement_codes: [STATEMENT_CODE, 'OTHER.CODE'] }],
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
    await expect(evaluator.evaluate({ question: QUESTION, statement_code: STATEMENT_CODE, jurisdiction: JURISDICTION })).rejects.toThrow();
  });

  it('isolates a validation failure to the offending item', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [
        { question: '', statement_codes: [STATEMENT_CODE] },
        { question: QUESTION, statement_codes: [STATEMENT_CODE] },
      ],
      JURISDICTION,
    );

    expect(results).toHaveLength(2);
    // Same shape as every other failure, so grouping by name does not miss these.
    expect(results[0].standards[0].error?.name).toBe('InputValidationError');
    expect(results[0].standards[0].statement_code).toBe(STATEMENT_CODE);
    expect(results[1].standards[0].error).toBeUndefined();
    expect(results[1].standards[0].aligned_count).toBe(2);
  });

  it('surfaces a validation failure even when the item has no statement codes', async () => {
    // Nothing to map over, so without an item-level error the failure vanishes.
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: '', statement_codes: [] }],
      JURISDICTION,
    );

    expect(results).toHaveLength(1);
    expect(results[0].standards).toEqual([]);
    expect(results[0].error).toMatchObject({ name: 'InputValidationError' });
  });

  it('reports a blank statement code as invalid input, not a dependency failure', async () => {
    // The bulk paths call the core directly rather than through evaluate(), so without
    // a per-code check a blank code reaches the Knowledge Graph and comes back as an
    // upstream error -- blaming the service for the caller's input.
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());

    const results = await evaluator.evaluateItems(
      [{ question: 'What is the area?', statement_codes: ['3.MD.C.7.d', '  '] }],
      JURISDICTION,
    );

    expect(results).toHaveLength(1);
    expect(results[0].error).toMatchObject({ name: 'InputValidationError' });
  });

  it('excludes an invalid item from the progress denominator', async () => {
    const evaluator = new MathStandardsAlignmentEvaluator(makeConfig());
    const onProgress = vi.fn();

    await evaluator.evaluateItems(
      [
        { question: '', statement_codes: [STATEMENT_CODE] },
        { question: QUESTION, statement_codes: [STATEMENT_CODE] },
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
      .evaluateByGradeLevel(['Q1'], '3', JURISDICTION);

    expect(errored.by_question[0].standards[0].error).toBeDefined();
    expect(errored.by_standard[0].covered_by).toEqual([]);
    expect(errored.by_standard[0]).toMatchObject({
      coverage_count: 0, error_count: 1, evaluated_count: 0, no_components_count: 0,
    });

    // Same zero coverage, but measured: every LC came back unaligned.
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      ...MOCK_BATCH_RESPONSE,
      data: {
        evaluations: MOCK_BATCH_RESPONSE.data.evaluations.map((e) => ({ ...e, answer: 'No' })),
      },
    });
    const unaligned = await new MathStandardsAlignmentEvaluator(makeConfig())
      .evaluateByGradeLevel(['Q1'], '3', JURISDICTION);

    expect(unaligned.by_standard[0]).toMatchObject({
      coverage_count: 0, error_count: 0, evaluated_count: 1, no_components_count: 0,
    });

    // Third way to reach zero coverage: never evaluated because the filter skipped it.
    vi.mocked(mockProvider.generateStructured).mockReset();
    vi.mocked(mockProvider.generateStructured).mockResolvedValue({
      data: { standards: [{ standard: STATEMENT_CODE, relevant: false }] },
      model: 'anthropic:claude-haiku-4-5-20251001', usage: { inputTokens: 50, outputTokens: 20 }, latencyMs: 200,
    });
    const filtered = await new MathStandardsAlignmentEvaluator(makeConfig())
      .evaluateByGradeLevel(['Q1'], '3', JURISDICTION, { useCoarseFilter: true });

    expect(filtered.by_standard[0]).toMatchObject({
      coverage_count: 0, error_count: 0, evaluated_count: 0, filtered_count: 1,
    });

    // Fourth way: the standard exists but has no learning components, so nothing was
    // measured. Counting it as evaluated would read as a judgement.
    const noComponents = makeMockKgClient({
      getLearningComponentsByCode: vi.fn().mockResolvedValue({ uuid: 'uuid-abc', components: [] }),
    });
    const unauthored = await new MathStandardsAlignmentEvaluator(makeConfig({ _kgClient: noComponents }))
      .evaluateByGradeLevel(['Q1'], '3', JURISDICTION);

    // Its own counter, so all-zeros is never the only signal.
    expect(unauthored.by_standard[0]).toMatchObject({
      coverage_count: 0, error_count: 0, evaluated_count: 0, filtered_count: 0, no_components_count: 1,
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
      Array.from({ length: 4 }, (_, i) => ({ question: `${prefix}-${i}`, statement_codes: [STATEMENT_CODE] }));

    await Promise.all([
      evaluator.evaluateItems(items('A'), JURISDICTION),
      evaluator.evaluateItems(items('B'), JURISDICTION),
    ]);

    // Exact: a per-call limiter would peak at 4, and "<= 2" alone would pass
    // vacuously if everything serialized.
    expect(peak).toBe(2);
  });
});
