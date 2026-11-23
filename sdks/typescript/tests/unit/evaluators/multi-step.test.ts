import { describe, it, expect, vi, beforeEach } from 'vitest';
import { z } from 'zod';
import {
  defineMultiStepEvaluator,
  requireConditionValues,
  requirePreprocessing,
} from '../../../src/evaluators/multi-step.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const sent = vi.fn();
const created: Array<{ type: string; model: string }> = [];
const calls: Array<{
  model: string;
  system: string;
  user: string;
  temperature?: number;
  /** The whole request, for checks on which keys were sent at all. */
  request: Record<string, unknown>;
  reasoningEffort?: string;
  maxTokens?: number;
}> = [];

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = sent;
  },
}));

// Each step's response is keyed by model so a two-model contract can be told apart.
const RESPONSES: Record<string, unknown> = {};

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => {
      created.push(config);
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn(
          (request: {
            messages: Array<{ role: string; content: string }>;
            temperature?: number;
            reasoningEffort?: string;
            maxTokens?: number;
          }) => {
            calls.push({
              model: config.model,
              system: request.messages[0].content,
              user: request.messages[1].content,
              temperature: request.temperature,
              request: request as unknown as Record<string, unknown>,
              // Recorded only when present, so a test can tell "absent" from undefined.
              ...('reasoningEffort' in request ? { reasoningEffort: request.reasoningEffort } : {}),
              ...('maxTokens' in request ? { maxTokens: request.maxTokens } : {}),
            });
            const canned = RESPONSES[config.model];
            if (canned instanceof Error) return Promise.reject(canned);
            return Promise.resolve({
              data: canned ?? { verdict: 'clear', reasoning: 'because' },
              model: config.model,
              usage: { inputTokens: 7, outputTokens: 3 },
              latencyMs: 12,
            });
          },
        ),
        generateText: vi.fn(),
      } as unknown as LLMProvider;
    }),
  };
});

/**
 * The factory carries the flow every multi-step evaluator runs — placeholder resolution,
 * conditional preprocessing, step ordering — so it is tested here against a synthetic
 * contract rather than only through sentence structure's.
 */

const ANALYSIS_SCHEMA = z.object({ count: z.number() });
const FINAL_SCHEMA = z.object({ verdict: z.string(), reasoning: z.string() });
type Final = z.infer<typeof FINAL_SCHEMA>;

const INPUT_SCHEMA = {
  properties: {
    text: { type: 'string', minLength: 1 },
    grade_level: { type: 'string', enum: ['3', '4', '5'] },
  },
  required: ['text', 'grade_level'],
} as const;

function contract(overrides: Record<string, unknown> = {}) {
  return {
    evaluator: {
      id: 'demo.area.thing',
      stable_id: '11111111-1111-1111-1111-111111111111',
      id_history: [],
      name: 'Thing Evaluator',
      description: 'Demonstration contract.',
    },
    steps: [
      {
        id: 'analyse',
        model: { provider: 'openai', name: 'gpt-analyse' },
        generation: { temperature: 0 },
        prompt: {
          placeholders: {
            text: { required: true, source: 'input' },
            counts: { required: true, source: 'preprocessing.counts' },
          },
        },
      },
      {
        id: 'classify',
        model: { provider: 'openai', name: 'gpt-classify' },
        generation: { temperature: 0.5 },
        prompt: {
          placeholders: {
            excerpt: { required: true, source: 'input.text' },
            grade_level: { required: true, source: 'input' },
            rubric: { required: true, source: 'preprocessing.rubric' },
            derived: { required: true, source: 'preprocessing.derived' },
            raw_analysis: { required: true, source: 'steps.analyse.output' },
          },
        },
      },
    ],
    preprocessing: [
      {
        id: 'counts',
        kind: 'custom',
        input: 'text',
        output: 'counts',
        implementation: { typescript: { library: 'custom', function: 'countWords' } },
      },
      {
        id: 'rubric_low',
        kind: 'load_rubric_text',
        input: 'grade_level',
        output: 'rubric',
        source_path: 'low.txt',
        condition: { input: 'grade_level', in: ['3'] },
        implementation: { typescript: { library: 'raw-loader', function: 'load' } },
      },
      {
        id: 'rubric_high',
        kind: 'load_rubric_text',
        input: 'grade_level',
        output: 'rubric',
        source_path: 'high.txt',
        condition: { input: 'grade_level', in: ['4', '5'] },
        implementation: { typescript: { library: 'raw-loader', function: 'load' } },
      },
      {
        id: 'derived',
        kind: 'custom',
        input: 'steps.analyse.output',
        output: 'derived',
        implementation: { typescript: { library: 'custom', function: 'describeAnalysis' } },
      },
    ],
    outcome: { score: 'verdict', reasoning: 'reasoning' },
    ...overrides,
  };
}

/** The shape the mutating tests below reach into. */
type Contract = ReturnType<typeof contract>;

const STEPS = {
  analyse: {
    system: 'analyse system',
    user: 'text={text} counts={counts}',
    schema: ANALYSIS_SCHEMA,
  },
  classify: {
    system: 'classify system',
    user: 'excerpt={excerpt} grade={grade_level} rubric={rubric} derived={derived} raw={raw_analysis}',
    schema: FINAL_SCHEMA,
  },
};

const COMPUTATIONS = {
  countWords: (input: unknown) => String(String(input).split(/\s+/).length),
  describeAnalysis: (input: unknown) => `count=${(input as { count: number }).count}`,
};

const DOCUMENTS = { 'low.txt': 'LOW RUBRIC', 'high.txt': 'HIGH RUBRIC' };

function define(overrides: Record<string, unknown> = {}) {
  return defineFrom(contract(overrides));
}

/** Build the class from an already-mutated contract, with the definition's other parts fixed. */
function defineFrom(
  source: Contract,
  parts: {
    steps?: typeof STEPS;
    computations?: typeof COMPUTATIONS;
    documents?: Record<string, string>;
  } = {},
) {
  return defineMultiStepEvaluator<{ text: string; grade_level: string }, Final>({
    contract: source as never,
    inputSchema: INPUT_SCHEMA as never,
    outputSchema: FINAL_SCHEMA,
    steps: (parts.steps ?? STEPS) as never,
    computations: parts.computations ?? COMPUTATIONS,
    documents: parts.documents ?? DOCUMENTS,
  });
}

function construct(Klass: ReturnType<typeof define>) {
  return new Klass({ openaiApiKey: 'k', telemetry: false });
}

beforeEach(() => {
  sent.mockClear();
  created.length = 0;
  calls.length = 0;
  RESPONSES['gpt-analyse'] = { count: 4 };
  RESPONSES['gpt-classify'] = { verdict: 'clear', reasoning: 'because' };
});

describe('defineMultiStepEvaluator', () => {
  it('runs the steps in the order the contract declares', async () => {
    await construct(define()).evaluate({ text: 'one two three four', grade_level: '3' });

    expect(calls.map((c) => c.model)).toEqual(['gpt-analyse', 'gpt-classify']);
  });

  it('resolves each placeholder from the source the contract names', async () => {
    await construct(define()).evaluate({ text: 'one two three four', grade_level: '3' });

    // `input` by placeholder name, `input.text` by field, `preprocessing.*` by output,
    // and `steps.*.output` as the prior step's payload.
    expect(calls[0].user).toBe('text=one two three four counts=4');
    expect(calls[1].user).toBe(
      'excerpt=one two three four grade=3 rubric=LOW RUBRIC derived=count=4 raw={"count":4}',
    );
  });

  it('picks the conditional entry that matches the input', async () => {
    await construct(define()).evaluate({ text: 'a b', grade_level: '5' });

    expect(calls[1].user).toContain('rubric=HIGH RUBRIC');
  });

  it('runs preprocessing that reads a step output after that step', async () => {
    RESPONSES['gpt-analyse'] = { count: 99 };

    await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(calls[1].user).toContain('derived=count=99');
  });

  it('passes a string step output through without quoting it', async () => {
    // JSON.stringify would wrap it in quotes and escape it, which would reach the prompt.
    RESPONSES['gpt-analyse'] = 'already text';

    const stringStep = contract();
    stringStep.preprocessing[3].input = 'text';

    await construct(defineFrom(stringStep)).evaluate({ text: 'a b', grade_level: '3' });

    expect(calls[1].user).toContain('raw=already text');
  });

  it('sends each step its own declared temperature', async () => {
    await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(calls.map((c) => c.temperature)).toEqual([0, 0.5]);
  });

  describe('output cap', () => {
    function withCaps(analyse?: number, classify?: number) {
      const source = contract();
      if (analyse) Object.assign(source.steps[0].generation, { max_output_tokens: analyse });
      if (classify) Object.assign(source.steps[1].generation, { max_output_tokens: classify });
      return source;
    }

    it('sends each step only the cap it declares, as maxTokens', async () => {
      await construct(defineFrom(withCaps(undefined, 800))).evaluate({ text: 'a b', grade_level: '3' });

      expect(calls[0]).not.toHaveProperty('maxTokens');
      expect(calls[1].maxTokens).toBe(800);
    });

    it('leaves the key off every request when the contract declares none', async () => {
      await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

      expect(calls.every((c) => !('maxTokens' in c))).toBe(true);
    });

    it('drops every cap under modelOverride', async () => {
      const Klass = defineFrom(withCaps(2000, 800));
      const evaluator = new Klass({
        anthropicApiKey: 'k',
        telemetry: false,
        modelOverride: { provider: 'anthropic' as never, model: 'claude-opus-5-5' },
      });
      await evaluator.evaluate({ text: 'a b', grade_level: '3' });

      expect(calls.every((c) => !('maxTokens' in c))).toBe(true);
    });

    it('does not hand an injected llmProvider the cap', async () => {
      const generateStructured = vi.fn().mockResolvedValue({
        data: { count: 2, verdict: 'clear', reasoning: 'because' },
        model: 'mine',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      });
      const llmProvider = { label: 'mine', generateStructured, generateText: vi.fn() };
      const Klass = defineFrom(withCaps(2000, 800));
      await new Klass({ telemetry: false, llmProvider }).evaluate({ text: 'a b', grade_level: '3' });

      expect(generateStructured).toHaveBeenCalledTimes(2);
      for (const [request] of generateStructured.mock.calls) {
        expect(request).not.toHaveProperty('maxTokens');
      }
    });
  });

  describe('reasoning effort', () => {
    function withEfforts(analyse?: string, classify?: string) {
      const source = contract();
      if (analyse) Object.assign(source.steps[0].generation, { reasoning_effort: analyse });
      if (classify) Object.assign(source.steps[1].generation, { reasoning_effort: classify });
      return source;
    }

    it('sends each step only the effort it declares', async () => {
      await construct(defineFrom(withEfforts('none'))).evaluate({ text: 'a b', grade_level: '3' });

      expect(calls[0].reasoningEffort).toBe('none');
      expect(calls[1]).not.toHaveProperty('reasoningEffort');
    });

    it('leaves the key off every request when the contract declares none', async () => {
      await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

      expect(calls.every((c) => !('reasoningEffort' in c))).toBe(true);
    });

    it('drops every effort under modelOverride', async () => {
      const Klass = defineFrom(withEfforts('none', 'low'));
      const evaluator = new Klass({
        anthropicApiKey: 'k',
        telemetry: false,
        modelOverride: { provider: 'anthropic' as never, model: 'claude-opus-5-5' },
      });
      await evaluator.evaluate({ text: 'a b', grade_level: '3' });

      expect(calls.every((c) => !('reasoningEffort' in c))).toBe(true);
    });

    it('does not hand an injected llmProvider the effort', async () => {
      const generateStructured = vi.fn().mockResolvedValue({
        data: { count: 2, verdict: 'clear', reasoning: 'because' },
        model: 'mine',
        usage: { inputTokens: 1, outputTokens: 1 },
        latencyMs: 1,
      });
      const llmProvider = { label: 'mine', generateStructured, generateText: vi.fn() };
      const Klass = defineFrom(withEfforts('none', 'low'));
      await new Klass({ telemetry: false, llmProvider }).evaluate({ text: 'a b', grade_level: '3' });

      expect(generateStructured).toHaveBeenCalledTimes(2);
      for (const [request] of generateStructured.mock.calls) {
        expect(request).not.toHaveProperty('reasoningEffort');
      }
    });
  });

  it('returns the last step output as the result', async () => {
    const result = await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(result.result).toEqual({ verdict: 'clear', reasoning: 'because' });
    expect(result.evaluator).toBe('demo.area.thing');
  });

  it('names every stage after the contract step id', async () => {
    // A stage named anything else is telemetry keyed on a name no contract uses, which is
    // how the previous hand-written implementation reported `complexity_classification`
    // for a step the contract calls `classify_complexity`.
    const evaluator = new (define())({ openaiApiKey: 'k' });
    await evaluator.evaluate({ text: 'a b', grade_level: '3' });

    const event = sent.mock.calls[0][0] as {
      metadata?: { stage_details?: Array<{ stage: string }> };
    };
    expect(event.metadata?.stage_details?.map((s) => s.stage)).toEqual(['analyse', 'classify']);
  });

  it('builds one provider per distinct model, not per step', async () => {
    await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(created.map((c) => c.model)).toEqual(['gpt-analyse', 'gpt-classify']);
  });

  it('shares one provider between steps on the same model', async () => {
    const shared = contract();
    shared.steps[1].model.name = 'gpt-analyse';

    await construct(defineFrom(shared)).evaluate({ text: 'a b', grade_level: '3' });

    expect(created).toHaveLength(1);
  });

  it('reports the model of the step that produced the result', async () => {
    const result = await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(result.metadata.model).toBe('openai:gpt-classify');
  });

  it('sums token usage across every step', async () => {
    const result = await construct(define()).evaluate({ text: 'a b', grade_level: '3' });

    expect(result.metadata.tokenUsage).toEqual({ inputTokens: 14, outputTokens: 6 });
  });
});

describe('defineMultiStepEvaluator — contract failures', () => {
  it('rejects a contract with fewer than two steps', () => {
    const single = contract();
    single.steps = [single.steps[0]];

    expect(() => defineFrom(single)).toThrow(/defineSingleStepEvaluator/);
  });

  it('rejects a step with no prompts supplied', () => {
    const renamed = contract();
    renamed.steps[1].id = 'unsupplied';

    expect(() => defineFrom(renamed)).toThrow(/No prompts supplied for step "unsupplied"/);
  });

  it('rejects a non-final step with no schema', () => {
    // Only a step that can end a run may omit one, since its output is then the result
    // and is validated against the definition's outputSchema.
    const steps = {
      analyse: { system: 'analyse system', user: 'text={text} counts={counts}' },
      classify: STEPS.classify,
    };

    expect(() => defineFrom(contract(), { steps: steps as never })).toThrow(
      /No schema supplied for step "analyse"/,
    );
  });

  it('rejects a custom computation the SDK does not supply', () => {
    expect(() =>
      defineFrom(contract(), { computations: { countWords: COMPUTATIONS.countWords } as never }),
    ).toThrow(/declares custom function "describeAnalysis"/);
  });

  it('rejects a document the SDK does not supply', () => {
    expect(() => defineFrom(contract(), { documents: { 'low.txt': 'LOW RUBRIC' } })).toThrow(
      /declares source_path "high.txt"/,
    );
  });

  it('fails when no conditional entry matches, rather than sending an empty placeholder', async () => {
    // Grade 4 is valid input, but neither rubric condition covers it.
    const narrowed = contract();
    narrowed.preprocessing[2].condition = { input: 'grade_level', in: ['5'] };

    const evaluator = construct(defineFrom(narrowed));

    await expect(evaluator.evaluate({ text: 'a b', grade_level: '4' })).rejects.toThrow(
      /No preprocessing entry produces "rubric"/,
    );
  });

  it('fails when two conditional entries match the same output', async () => {
    const overlapping = contract();
    overlapping.preprocessing[2].condition = { input: 'grade_level', in: ['3', '4', '5'] };

    const evaluator = construct(defineFrom(overlapping));

    await expect(evaluator.evaluate({ text: 'a b', grade_level: '3' })).rejects.toThrow(
      /mutually exclusive/,
    );
  });

  it('rejects an unknown placeholder source', async () => {
    const bad = contract();
    bad.steps[1].prompt.placeholders.excerpt = { required: true, source: 'nowhere.text' };

    const evaluator = construct(defineFrom(bad));

    await expect(evaluator.evaluate({ text: 'a b', grade_level: '3' })).rejects.toThrow(
      /unsupported source "nowhere.text"/,
    );
  });

  it('runs a library preprocessing entry, as a single-step contract would', async () => {
    // `custom` and `load_rubric_text` are not the only kinds a multi-step contract may
    // declare; vocabulary-complexity's grade-conditioned `flesch_kincaid_grade` is the
    // reason this branch exists.
    const withLibrary = contract();
    withLibrary.preprocessing[0] = {
      id: 'fk',
      kind: 'flesch_kincaid_grade',
      input: 'text',
      output: 'counts',
      implementation: {
        typescript: {
          library: 'text-readability',
          function: 'fleschKincaidGrade',
          post_transform: { type: 'round', precision: 2 },
        },
      },
    } as never;

    await construct(defineFrom(withLibrary)).evaluate({
      text: 'The cat sat on the mat. It was warm and soft.',
      grade_level: '3',
    });

    // The value text-readability produces for this text, rounded as the contract declares.
    expect(calls[0].user).toBe('text=The cat sat on the mat. It was warm and soft. counts=-1.7');
  });

  it('fails when preprocessing reads a step that has not run', async () => {
    // An entry pointing at a later step: the guard is what stops `undefined` reaching the
    // computation and being stringified into the prompt.
    const forwardRef = contract();
    forwardRef.preprocessing[0].input = 'steps.classify.output';

    await expect(
      construct(defineFrom(forwardRef)).evaluate({ text: 'a b', grade_level: '3' }),
    ).rejects.toThrow(/reads "steps.classify.output", which is not available yet/);
  });

  it('telemeters an error with only the stages that completed', async () => {
    RESPONSES['gpt-classify'] = new Error('provider exploded');

    const evaluator = new (define())({ openaiApiKey: 'k' });
    await expect(evaluator.evaluate({ text: 'a b', grade_level: '3' })).rejects.toThrow();

    const event = sent.mock.calls[0][0] as {
      status: string;
      token_usage?: { input_tokens: number };
      metadata?: { stage_details?: Array<{ stage: string }> };
    };
    expect(event.status).toBe('error');
    // The first step succeeded, so its stage and its tokens are still reported.
    expect(event.metadata?.stage_details?.map((s) => s.stage)).toEqual(['analyse']);
    expect(event.token_usage?.input_tokens).toBe(7);
  });

  it('rejects a provider the SDK does not support', () => {
    const alien = contract();
    alien.steps[0].model.provider = 'some-other-vendor';

    expect(() => defineFrom(alien)).toThrow(/Unsupported provider "some-other-vendor"/);
  });

  it('fails when a placeholder reads a step that has not run', async () => {
    // A forward reference: the first step cannot read the second one's output.
    const forward = contract();
    forward.steps[0].prompt.placeholders.counts = {
      required: true,
      source: 'steps.classify.output',
    };

    await expect(
      construct(defineFrom(forward)).evaluate({ text: 'a b', grade_level: '3' }),
    ).rejects.toThrow(/reads step "classify", which has not run/);
  });

  it('still returns a result when telemetry fails on success', async () => {
    // Telemetry is fire-and-forget: a failing collector must not fail an evaluation.
    sent.mockRejectedValueOnce(new Error('collector down'));

    const evaluator = new (define())({ openaiApiKey: 'k' });
    const result = await evaluator.evaluate({ text: 'a b', grade_level: '3' });

    expect(result.result).toEqual({ verdict: 'clear', reasoning: 'because' });
  });

  it('still throws the original error when telemetry fails on error', async () => {
    // The provider's failure is what the caller needs to see, not the collector's.
    RESPONSES['gpt-analyse'] = new Error('provider exploded');
    sent.mockRejectedValueOnce(new Error('collector down'));

    const evaluator = new (define())({ openaiApiKey: 'k' });

    await expect(evaluator.evaluate({ text: 'a b', grade_level: '3' })).rejects.toThrow(
      /provider exploded/,
    );
  });

  it('attributes a failure to the step that was running, not the last one', async () => {
    // The steps here use different vendors, which is the case that exposes it — with one
    // shared provider the wrong attribution is indistinguishable from the right one.
    const twoVendors = contract();
    twoVendors.steps[1].model = { provider: 'google', name: 'gemini-classify' };
    RESPONSES['gpt-analyse'] = new Error('first step exploded');

    const evaluator = new (defineFrom(twoVendors))({
      openaiApiKey: 'k',
      googleApiKey: 'k',
    });
    await expect(evaluator.evaluate({ text: 'a b', grade_level: '3' })).rejects.toThrow();

    const event = sent.mock.calls[0][0] as { provider?: string };
    expect(event.provider).toBe('openai:gpt-analyse');
  });

  it('fails a library preprocessing entry that reads an unavailable step', async () => {
    // The guard used to sit inside the `custom` branch only, so this ran the computation on
    // the empty string and produced a plausible number instead of an error.
    const forwardLibrary = contract();
    forwardLibrary.preprocessing[0] = {
      id: 'fk',
      kind: 'flesch_kincaid_grade',
      input: 'steps.classify.output',
      output: 'counts',
      implementation: {
        typescript: { library: 'text-readability', function: 'fleschKincaidGrade' },
      },
    } as never;

    await expect(
      construct(defineFrom(forwardLibrary)).evaluate({ text: 'a b', grade_level: '3' }),
    ).rejects.toThrow(/reads "steps.classify.output", which is not available yet/);
  });

  it('validates inputs before running any step', async () => {
    await expect(
      construct(define()).evaluate({ text: '', grade_level: '3' }),
    ).rejects.toThrow();

    expect(calls).toHaveLength(0);
  });
});

/**
 * One contract carrying two configurations, split on grade: an analyse/classify pair for
 * grade 3 and another for grades 4 and 5, each pair on its own model. This is the shape
 * sentence structure's contract has.
 */
function banded() {
  const base = contract();
  const [analyse, classify] = base.steps;
  const low = { input: 'grade_level', in: ['3'] };
  const high = { input: 'grade_level', in: ['4', '5'] };
  const classifyFor = (band: string, model: string, condition: typeof low) => ({
    ...classify,
    id: `classify_${band}`,
    condition,
    model: { provider: 'openai', name: model },
    generation: { temperature: 0.5, reasoning_effort: 'none' },
    prompt: {
      placeholders: {
        ...classify.prompt.placeholders,
        raw_analysis: { required: true, source: `steps.analyse_${band}.output` },
      },
    },
  });
  const derivedFor = (band: string, condition: typeof low) => ({
    ...base.preprocessing[3],
    id: `derived_${band}`,
    input: `steps.analyse_${band}.output`,
    condition,
  });
  return {
    ...base,
    steps: [
      { ...analyse, id: 'analyse_low', condition: low, model: { provider: 'openai', name: 'gpt-low' } },
      { ...analyse, id: 'analyse_high', condition: high, model: { provider: 'openai', name: 'gpt-high' } },
      classifyFor('low', 'gpt-low', low),
      classifyFor('high', 'gpt-high', high),
    ],
    preprocessing: [
      ...base.preprocessing.slice(0, 3),
      derivedFor('low', low),
      derivedFor('high', high),
    ],
  };
}

type Banded = ReturnType<typeof banded>;

const BANDED_STEPS = {
  analyse_low: STEPS.analyse,
  analyse_high: STEPS.analyse,
  // No schema: each ends the run for its band, so it takes the definition's outputSchema.
  classify_low: { system: STEPS.classify.system, user: STEPS.classify.user },
  classify_high: { system: STEPS.classify.system, user: STEPS.classify.user },
};

function defineBanded(source: Banded = banded(), steps: Record<string, unknown> = BANDED_STEPS) {
  return defineFrom(source as never, { steps: steps as never });
}

describe('defineMultiStepEvaluator — conditional steps', () => {
  beforeEach(() => {
    RESPONSES['gpt-low'] = { count: 4, verdict: 'low verdict', reasoning: 'low' };
    RESPONSES['gpt-high'] = { count: 9, verdict: 'high verdict', reasoning: 'high' };
  });

  it.each([
    ['3', 'gpt-low', 'low verdict'],
    ['5', 'gpt-high', 'high verdict'],
  ])('at grade %s runs only the steps whose condition holds, in declared order', async (grade, model, verdict) => {
    const evaluator = new (defineBanded())({ openaiApiKey: 'k' });
    const result = await evaluator.evaluate({ text: 'a b', grade_level: grade });

    expect(calls.map((c) => c.model)).toEqual([model, model]);
    expect(calls.map((c) => c.system)).toEqual(['analyse system', 'classify system']);

    // The result is the last step that ran, not the last one declared — which for grade 3
    // is a step that never ran — and the reported model is that step's.
    expect(result.result).toMatchObject({ verdict });
    expect(result.metadata.model).toBe(`openai:${model}`);

    const band = model.slice('gpt-'.length);
    const event = sent.mock.calls[0][0] as {
      provider: string;
      metadata?: { stage_details?: Array<{ stage: string; provider: string }> };
    };
    expect(event.provider).toBe(`openai:${model}`);
    expect(event.metadata?.stage_details).toMatchObject([
      { stage: `analyse_${band}`, provider: `openai:${model}` },
      { stage: `classify_${band}`, provider: `openai:${model}` },
    ]);
  });

  it('reads the step output of the band that ran', async () => {
    await construct(defineBanded()).evaluate({ text: 'a b', grade_level: '5' });

    // The other band's entry reads a step that did not run, and is not applicable.
    expect(calls[1].user).toContain('derived=count=9');
    expect(calls[1].user).toContain('raw={"count":9');
  });

  it('reports the right model for each of two overlapping evaluations', async () => {
    // The reported provider is per evaluation; held on the instance, the later call
    // would overwrite the earlier one's.
    const evaluator = construct(defineBanded());
    const [low, high] = await Promise.all([
      evaluator.evaluate({ text: 'a b', grade_level: '3' }),
      evaluator.evaluate({ text: 'a b', grade_level: '5' }),
    ]);

    expect(low.metadata.model).toBe('openai:gpt-low');
    expect(high.metadata.model).toBe('openai:gpt-high');
  });

  it('fails an applicable entry that reads a step which did not run', async () => {
    const crossed = banded();
    crossed.preprocessing[4].input = 'steps.analyse_low.output';

    await expect(
      construct(defineBanded(crossed)).evaluate({ text: 'a b', grade_level: '5' }),
    ).rejects.toThrow(/reads "steps.analyse_low.output", which is not available yet/);
  });

  it('fails when no step applies to the inputs', async () => {
    const narrowed = banded();
    for (const step of narrowed.steps) {
      if (step.condition.in.includes('4')) step.condition = { input: 'grade_level', in: ['5'] };
    }

    await expect(
      construct(defineBanded(narrowed)).evaluate({ text: 'a b', grade_level: '4' }),
    ).rejects.toMatchObject({
      name: 'ConfigurationError',
      message: expect.stringContaining('No step of Thing Evaluator applies'),
    });
    expect(calls).toHaveLength(0);
  });

  it('fails when the run would end on a step whose output is not the result', async () => {
    // An unconditional step with another declared after it is an intermediate one. Grade 4
    // runs it and then nothing, so there is no result to return.
    const gap = contract();
    (gap.steps[1] as { condition?: unknown }).condition = { input: 'grade_level', in: ['3'] };

    await expect(
      construct(defineFrom(gap)).evaluate({ text: 'a b', grade_level: '4' }),
    ).rejects.toMatchObject({
      name: 'ConfigurationError',
      message: expect.stringContaining('Step "analyse" is the last'),
    });
    expect(calls).toHaveLength(0);
  });

  it('ends on a step declared with the output schema when no later step covers the inputs', async () => {
    // The same gap, but the unconditional step produces the result itself and the step
    // after it is a refinement only grade 3 gets. Grade 4 has a result: the first step's.
    const refined = contract();
    (refined.steps[1] as { condition?: unknown }).condition = { input: 'grade_level', in: ['3'] };
    const steps = { ...STEPS, analyse: { ...STEPS.analyse, schema: FINAL_SCHEMA } };
    const firstModel = refined.steps[0].model.name;
    RESPONSES[firstModel] = { verdict: 'first verdict', reasoning: 'first' };

    const evaluator = construct(defineFrom(refined, { steps: steps as never }));
    const result = await evaluator.evaluate({ text: 'a b', grade_level: '4' });

    expect(calls).toHaveLength(1);
    expect(result.result).toMatchObject({ verdict: 'first verdict' });
    expect(result.metadata.model).toBe(`${refined.steps[0].model.provider}:${firstModel}`);
  });

  it.each([
    ['3', 'gpt-low'],
    ['5', 'gpt-high'],
  ])('at grade %s follows conditions the contract writes as numbers', async (grade, model) => {
    // config.schema.json admits numbers in condition.in; a caller's grade is a string.
    const numeric = banded();
    const asNumbers = (condition: { input: string; in: string[] }) =>
      ({ input: condition.input, in: condition.in.map(Number) }) as never;
    for (const step of numeric.steps) step.condition = asNumbers(step.condition);
    for (const entry of numeric.preprocessing) {
      const conditional = entry as { condition?: { input: string; in: string[] } };
      if (conditional.condition) conditional.condition = asNumbers(conditional.condition);
    }

    const evaluator = new (defineBanded(numeric))({ openaiApiKey: 'k' });
    const result = await evaluator.evaluate({ text: 'a b', grade_level: grade });

    expect(calls.map((c) => c.model)).toEqual([model, model]);
    expect(result.metadata.model).toBe(`openai:${model}`);
  });

  it('attributes a failure to the step of the band that was running', async () => {
    RESPONSES['gpt-high'] = new Error('high band exploded');

    const evaluator = new (defineBanded())({ openaiApiKey: 'k' });
    await expect(evaluator.evaluate({ text: 'a b', grade_level: '5' })).rejects.toThrow();

    const event = sent.mock.calls[0][0] as { provider?: string };
    expect(event.provider).toBe('openai:gpt-high');
  });

  it('rejects a missing schema on a conditional step that a later step always follows', () => {
    // Every grade analyse_low runs for, classify_low runs for too, so it never ends a run.
    const steps = { ...BANDED_STEPS, analyse_low: BANDED_STEPS.classify_low };

    expect(() => defineBanded(banded(), steps)).toThrow(/No schema supplied for step "analyse_low"/);
  });

  it('accepts a missing schema on each conditional step that can end a run', () => {
    expect(() => defineBanded()).not.toThrow();
  });
});

describe('defineMultiStepEvaluator — reasoning effort', () => {
  beforeEach(() => {
    RESPONSES['gpt-low'] = { count: 4, verdict: 'low verdict', reasoning: 'low' };
    RESPONSES['gpt-high'] = { count: 9, verdict: 'high verdict', reasoning: 'high' };
  });

  it('sends a step its declared reasoning effort, and nothing to a step declaring none', async () => {
    await construct(defineBanded()).evaluate({ text: 'a b', grade_level: '3' });

    // The analyse steps declare none; the key is absent rather than undefined.
    expect(calls[0].request).not.toHaveProperty('reasoningEffort');
    expect(calls[1].request.reasoningEffort).toBe('none');
  });

  it('withholds it under modelOverride, where the declared model is not what runs', async () => {
    const evaluator = new (defineBanded())({
      openaiApiKey: 'k',
      telemetry: false,
      modelOverride: { provider: 'openai' as never, model: 'gpt-override' },
    });
    await evaluator.evaluate({ text: 'a b', grade_level: '3' });

    expect(calls.map((c) => c.model)).toEqual(['gpt-override', 'gpt-override']);
    for (const call of calls) expect(call.request).not.toHaveProperty('reasoningEffort');
    // Temperature is unaffected by the override, as before.
    expect(calls.map((c) => c.temperature)).toEqual([0, 0.5]);
  });

  it('withholds it from an injected llmProvider', async () => {
    const requests: Array<Record<string, unknown>> = [];
    const llmProvider = {
      label: 'mine',
      generateStructured: vi.fn(async (request: Record<string, unknown>) => {
        requests.push(request);
        return {
          data: { count: 4, verdict: 'v', reasoning: 'r' },
          model: 'mine',
          usage: { inputTokens: 1, outputTokens: 1 },
          latencyMs: 1,
        };
      }),
      generateText: vi.fn(),
    } as unknown as LLMProvider;

    await new (defineBanded())({ llmProvider, telemetry: false }).evaluate({
      text: 'a b',
      grade_level: '3',
    });

    expect(requests).toHaveLength(2);
    for (const request of requests) expect(request).not.toHaveProperty('reasoningEffort');
  });
});

describe('requireConditionValues', () => {
  it('returns the declared values as strings', () => {
    // Numeric grades in a contract would otherwise compare unequal to the string inputs
    // an evaluator is handed.
    expect(
      requireConditionValues({ id: 's', condition: { input: 'grade_level', in: ['3', '4'] } }, 'X'),
    ).toEqual(['3', '4']);
    expect(
      requireConditionValues(
        { id: 's', condition: { input: 'grade_level', in: [3, 4] as never } },
        'X',
      ),
    ).toEqual(['3', '4']);
  });

  it('refuses a step that declares no condition', () => {
    // Routing that depends on the condition would silently take the other branch.
    expect(() => requireConditionValues({ id: 'branch' }, 'Thing Evaluator')).toThrow(
      /Step "branch" in Thing Evaluator config.json declares no condition.in/,
    );
  });

  it('refuses an empty condition', () => {
    expect(() =>
      requireConditionValues({ id: 'branch', condition: { input: 'grade_level', in: [] } }, 'X'),
    ).toThrow(/declares no condition.in/);
  });
});

describe('requirePreprocessing', () => {
  it('returns the entry a contract declares', () => {
    const entry = { id: 'fk_score', condition: { input: 'grade_level', in: ['3'] } };

    expect(requirePreprocessing({ preprocessing: [entry] }, 'fk_score')).toBe(entry);
  });

  it('refuses an entry the contract does not declare', () => {
    // Read by id, so a contract that stops declaring it should fail at load rather than
    // silently skip the computation.
    expect(() =>
      requirePreprocessing({ evaluator: { name: 'Thing Evaluator' }, preprocessing: [] }, 'fk_score'),
    ).toThrow(/Preprocessing "fk_score" not found in Thing Evaluator config.json/);

    // Still legible when the contract carries no name.
    expect(() => requirePreprocessing({}, 'fk_score')).toThrow(/not found in the config.json/);
  });
});
