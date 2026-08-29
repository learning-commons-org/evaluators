import { describe, it, expect, vi, beforeEach } from 'vitest';
import { z } from 'zod';
import { defineMultiStepEvaluator } from '../../../src/evaluators/multi-step.js';
import type { LLMProvider } from '../../../src/providers/base.js';

const sent = vi.fn();
const created: Array<{ type: string; model: string }> = [];
const calls: Array<{ model: string; system: string; user: string; temperature?: number }> = [];

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
          }) => {
            calls.push({
              model: config.model,
              system: request.messages[0].content,
              user: request.messages[1].content,
              temperature: request.temperature,
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
    // Only the last step may omit one, since its output is the result and is validated
    // against the definition's outputSchema.
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
