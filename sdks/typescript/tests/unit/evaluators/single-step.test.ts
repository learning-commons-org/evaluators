import { describe, it, expect, vi, beforeEach } from 'vitest';
import { z } from 'zod';
import { defineSingleStepEvaluator, requireStep } from '../../../src/evaluators/single-step.js';
import { Provider } from '../../../src/evaluators/base.js';
import {
  EvaluatorError,
  InputValidationError,
  LLMOutputProcessingError,
} from '../../../src/errors.js';
import type { LLMProvider, LLMResponse } from '../../../src/providers/base.js';
import { runPreprocessingStep } from '../../../src/features/preprocessing.js';

const sent = vi.fn();
const created: Array<{ type: string; model: string; apiKey?: string }> = [];

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = sent;
  },
}));

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string; apiKey?: string }) => {
      created.push(config);
      return {
        label: `${config.type}:${config.model}`,
        generateStructured: vi.fn().mockResolvedValue({
          data: { verdict: 'clear', reasoning: 'because' },
          model: config.model,
          usage: { inputTokens: 7, outputTokens: 3 },
          latencyMs: 12,
        }),
        generateText: vi.fn(),
      };
    }),
  };
});

/**
 * The factory carries the flow every single-step evaluator runs, so what it reads from a
 * contract is tested here directly rather than only through one evaluator's contract.
 */

const OUTPUT_SCHEMA = z.object({ verdict: z.string(), reasoning: z.string() });
type Output = z.infer<typeof OUTPUT_SCHEMA>;

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
      id_history: ['demo.area.old_thing'],
      name: 'Thing Evaluator',
      description: 'Demonstration contract.',
      // Deliberately wider than the grade input's enum, which is what the factory used to
      // publish: the two are allowed to differ for an evaluator that takes no grade, and
      // this is the only way to tell which source the factory actually read.
      supported_grades: ['3', '4', '5', '6'],
    },
    steps: [
      {
        id: 'evaluate_thing',
        model: { provider: 'google', name: 'gemini-3-flash-preview' },
        generation: { temperature: 0.5 },
        prompt: { placeholders: { text: {}, grade_level: {}, fk_score: {} } },
        required_credentials: ['google_api_key'],
      },
    ],
    outcome: { score: 'verdict', reasoning: 'reasoning' },
    ...overrides,
  };
}

function define(overrides: Record<string, unknown> = {}) {
  return defineSingleStepEvaluator<{ text: string; grade_level: string }, Output>({
    // The synthetic contract is structurally what a real one is; the cast keeps the test
    // from restating every optional field the interface allows.
    contract: contract(overrides) as never,
    inputSchema: INPUT_SCHEMA as never,
    outputSchema: OUTPUT_SCHEMA,
    systemPrompt: 'system: {text} at {grade_level} with {fk_score}',
    userPrompt: 'user: {text} at {grade_level} with {fk_score}',
  });
}

/** Annotated, so a field the provider interface requires cannot be left out. */
const RESPONSE: LLMResponse<Output> = {
  data: { verdict: 'clear', reasoning: 'because' },
  model: 'gemini-3-flash-preview',
  usage: { inputTokens: 7, outputTokens: 3 },
  latencyMs: 12,
};

function fakeProvider(): LLMProvider {
  return {
    label: 'google:gemini-3-flash-preview',
    generateStructured: vi.fn().mockResolvedValue(RESPONSE),
    generateText: vi.fn(),
  };
}

const INPUT = { text: 'The cat sat on the mat.', grade_level: '4' };

// --- what the factory refuses to build ---

describe('defineSingleStepEvaluator rejects a contract it cannot run', () => {
  it('names the step it expected when the convention is not met', () => {
    expect(() => define({ steps: [{ id: 'not_the_convention', model: { provider: 'google', name: 'm' }, prompt: { placeholders: {} } }] })).toThrow(
      'evaluate_thing',
    );
  });

  it('names the evaluator whose contract is wrong', () => {
    expect(() => define({ steps: [{ id: 'wrong', model: { provider: 'google', name: 'm' }, prompt: { placeholders: {} } }] })).toThrow(
      'Thing Evaluator',
    );
  });

  it('rejects a provider the SDK has no adapter for, listing the ones it has', () => {
    expect(() =>
      define({ steps: [{ id: 'evaluate_thing', model: { provider: 'cohere', name: 'm' }, prompt: { placeholders: {} } }] }),
    ).toThrow(/Unsupported provider "cohere".*google/s);
  });
});

// --- what it reads from the contract ---

describe('defineSingleStepEvaluator reads its behaviour from the contract', () => {
  it('derives metadata rather than restating it', () => {
    const E = define();

    expect(E.metadata.id).toBe('demo.area.thing');
    expect(E.metadata.stableId).toBe('11111111-1111-1111-1111-111111111111');
    expect(E.metadata.idHistory).toEqual(['demo.area.old_thing']);
    expect(E.metadata.name).toBe('Thing Evaluator');
  });

  it('takes supported grades from the contract, not the grade input', () => {
    // The contract declares four grades and the input enum three, so this fails if the
    // factory goes back to deriving the field from the input schema.
    expect(define().metadata.supportedGrades).toEqual(['3', '4', '5', '6']);
  });

  it('takes the default provider from the declared step, not a hardcoded vendor', () => {
    expect(define().metadata.defaultProviders).toEqual([Provider.Google]);
  });

  it('requires the credentials the step declares', () => {
    expect(define().metadata.requiredCredentials).toEqual(['google_api_key']);
  });

  it('sends the temperature the step declares', async () => {
    const provider = fakeProvider();
    await new (define())({ llmProvider: provider, telemetry: false }).evaluate(INPUT);

    expect(vi.mocked(provider.generateStructured).mock.calls[0][0].temperature).toBe(0.5);
  });

  it('sends no temperature when the step declares none', async () => {
    const provider = fakeProvider();
    const E = define({
      steps: [{ id: 'evaluate_thing', model: { provider: 'google', name: 'm' }, prompt: { placeholders: {} } }],
    });
    await new E({ llmProvider: provider, telemetry: false }).evaluate(INPUT);

    expect(vi.mocked(provider.generateStructured).mock.calls[0][0].temperature).toBeUndefined();
  });

  it('runs each declared preprocessing step and passes it under its own id', async () => {
    const provider = fakeProvider();
    const E = define({
      preprocessing: [
        {
          id: 'fk_score',
          implementation: {
            typescript: {
              library: 'text-readability',
              function: 'fleschKincaidGrade',
              post_transform: { type: 'round', precision: 2 },
            },
          },
        },
      ],
    });

    await new E({ llmProvider: provider, telemetry: false }).evaluate(INPUT);

    const messages = vi.mocked(provider.generateStructured).mock.calls[0][0].messages;
    const expected = String(
      runPreprocessingStep(INPUT.text, {
        library: 'text-readability',
        function: 'fleschKincaidGrade',
        post_transform: { type: 'round', precision: 2 },
      }),
    );

    expect(messages.map((m) => m.role)).toEqual(['system', 'user']);
    // Both templates carry the placeholder, so both must be rendered.
    expect(messages[0].content).toContain(expected);
    expect(messages[1].content).toContain(expected);
    expect(messages[1].content).not.toContain('{fk_score}');
    // The declared inputs are substituted too, not only the preprocessed one.
    expect(messages[1].content).toContain(INPUT.text);
    expect(messages[1].content).toContain(INPUT.grade_level);
  });

  it('refuses a preprocessing library it has no adapter for', async () => {
    const E = define({
      preprocessing: [
        { id: 'x', implementation: { typescript: { library: 'not-installed', function: 'f' } } },
      ],
    });

    await expect(
      new E({ llmProvider: fakeProvider(), telemetry: false }).evaluate(INPUT),
    ).rejects.toThrow(/Unsupported preprocessing library "not-installed"/);
  });
});

// --- the envelope ---

describe('defineSingleStepEvaluator returns the result envelope', () => {
  it('reports the evaluator, payload, model and token usage', async () => {
    const provider = fakeProvider();
    const result = await new (define())({ llmProvider: provider, telemetry: false }).evaluate(INPUT);

    expect(result.evaluator).toBe('demo.area.thing');
    expect(result.result).toEqual({ verdict: 'clear', reasoning: 'because' });
    expect(result.metadata.model).toBe('google:gemini-3-flash-preview');
    expect(result.metadata.tokenUsage).toEqual({ inputTokens: 7, outputTokens: 3 });
    expect(result.metadata.processingTimeMs).toBeGreaterThanOrEqual(0);
  });

  it('validates inputs against the schema before calling the model', async () => {
    const provider = fakeProvider();

    await expect(
      new (define())({ llmProvider: provider, telemetry: false }).evaluate({
        text: '',
        grade_level: '4',
      }),
    ).rejects.toThrow(InputValidationError);
    expect(provider.generateStructured).not.toHaveBeenCalled();
  });

  it('rejects a grade the schema does not declare', async () => {
    await expect(
      new (define())({ llmProvider: fakeProvider(), telemetry: false }).evaluate({
        text: 'ok',
        grade_level: '9',
      }),
    ).rejects.toThrow(InputValidationError);
  });

  it('rejects an unknown input field', async () => {
    await expect(
      new (define())({ llmProvider: fakeProvider(), telemetry: false }).evaluate({
        text: 'ok',
        grade_level: '4',
        extra: 'no',
      } as never),
    ).rejects.toThrow(InputValidationError);
  });
});

// --- errors ---

describe('defineSingleStepEvaluator error handling', () => {
  it('passes an evaluator error through untouched', async () => {
    const provider = fakeProvider();
    const raised = new LLMOutputProcessingError('schema mismatch');
    vi.mocked(provider.generateStructured).mockRejectedValue(raised);

    await expect(
      new (define())({ llmProvider: provider, telemetry: false }).evaluate(INPUT),
    ).rejects.toBe(raised);
  });

  it('wraps a provider failure that is not already an evaluator error', async () => {
    const provider = fakeProvider();
    vi.mocked(provider.generateStructured).mockRejectedValue(new Error('socket hang up'));

    // A raw Error also has name 'Error', so assert the class the SDK is required to
    // surface — otherwise "rethrow everything untouched" passes this test.
    await expect(
      new (define())({ llmProvider: provider, telemetry: false }).evaluate(INPUT),
    ).rejects.toBeInstanceOf(EvaluatorError);
  });
});

// --- the paths llmProvider injection bypasses ---

describe('defineSingleStepEvaluator picks the key for the declared vendor', () => {
  // Every evaluator used to name `config.googleApiKey` itself. The vendor now comes from
  // the contract, so the key has to be selected from it too, and nothing else covers that.
  beforeEach(() => {
    created.length = 0;
    sent.mockClear();
    sent.mockResolvedValue(undefined);
  });

  it('hands a Google step the Google key', () => {
    new (define())({ googleApiKey: 'g-key', openaiApiKey: 'o-key', telemetry: false });

    expect(created[0]).toMatchObject({ type: 'google', apiKey: 'g-key' });
  });

  it('hands an OpenAI step the OpenAI key', () => {
    const E = define({
      steps: [
        {
          id: 'evaluate_thing',
          model: { provider: 'openai', name: 'gpt-4.1' },
          prompt: { placeholders: {} },
          required_credentials: ['openai_api_key'],
        },
      ],
    });
    new E({ googleApiKey: 'g-key', openaiApiKey: 'o-key', telemetry: false });

    expect(created[0]).toMatchObject({ type: 'openai', apiKey: 'o-key' });
  });

  it('constructs the model the step declares', () => {
    new (define())({ googleApiKey: 'g-key', telemetry: false });

    expect(created[0].model).toBe('gemini-3-flash-preview');
  });
});

describe('defineSingleStepEvaluator telemetry', () => {
  beforeEach(() => {
    created.length = 0;
    sent.mockClear();
    sent.mockResolvedValue(undefined);
  });

  it('reports a success with its token usage and stage', async () => {
    await new (define())({ googleApiKey: 'k' }).evaluate(INPUT);

    expect(sent).toHaveBeenCalledTimes(1);
    expect(sent.mock.calls[0][0]).toMatchObject({
      status: 'success',
      token_usage: { input_tokens: 7, output_tokens: 3 },
    });
  });

  it('names the step in stage_details so a multi-step successor stays comparable', async () => {
    await new (define())({ googleApiKey: 'k' }).evaluate(INPUT);

    const event = sent.mock.calls[0][0] as { metadata?: { stage_details?: Array<{ stage: string }> } };
    expect(event.metadata?.stage_details?.[0]?.stage).toBe('evaluate_thing');
  });

  it('reports a validation failure as an error event, not silence', async () => {
    // §4: validation runs inside the error-handling boundary.
    await expect(
      new (define())({ googleApiKey: 'k' }).evaluate({ text: '', grade_level: '4' }),
    ).rejects.toThrow(InputValidationError);

    expect(sent).toHaveBeenCalledTimes(1);
    expect(sent.mock.calls[0][0]).toMatchObject({
      status: 'error',
      error_code: 'InputValidationError',
    });
  });
});

// --- observability must not break the evaluation ---

describe('defineSingleStepEvaluator survives its own reporting failing', () => {
  beforeEach(() => {
    created.length = 0;
    sent.mockClear();
  });

  it('returns the result when telemetry cannot be sent', async () => {
    // Telemetry is fire-and-forget; a collector being down is not the caller's problem.
    sent.mockRejectedValue(new Error('collector unreachable'));

    const result = await new (define())({ googleApiKey: 'k' }).evaluate(INPUT);

    expect(result.result).toEqual({ verdict: 'clear', reasoning: 'because' });
  });

  it('propagates the original failure when error telemetry cannot be sent', async () => {
    sent.mockRejectedValue(new Error('collector unreachable'));

    // The caller must see the validation error, not the telemetry one.
    await expect(
      new (define())({ googleApiKey: 'k' }).evaluate({ text: '', grade_level: '4' }),
    ).rejects.toThrow(InputValidationError);
  });

  it('reports the tokens already spent when a failure follows a completed step', async () => {
    // The only way past the model call and into the catch: a caller-supplied logger that
    // throws. Contrived, but it is what makes the token aggregation in the catch reachable
    // — and a caller that loses spend data on failure would have a real complaint.
    sent.mockResolvedValue(undefined);
    const logger = {
      debug: vi.fn(),
      info: vi.fn((message: string) => {
        if (message.includes('completed successfully')) throw new Error('logger blew up');
      }),
      warn: vi.fn(),
      error: vi.fn(),
    };

    await expect(new (define())({ googleApiKey: 'k', logger }).evaluate(INPUT)).rejects.toThrow();

    // Success telemetry is sent before the completion log, so this evaluation reports
    // twice — a success then an error. Pre-existing ordering, noted rather than changed.
    const events = sent.mock.calls.map(([e]) => e as { status: string; token_usage?: unknown });
    expect(events.map((e) => e.status)).toEqual(['success', 'error']);
    expect(events[1].token_usage).toEqual({ input_tokens: 7, output_tokens: 3 });
  });
});

// --- the shared step lookup ---

describe('requireStep', () => {
  // Both the factory and Sentence Structure resolve steps through this, so a missing step
  // has to fail the same way for either.
  const steps = [{ id: 'first' }, { id: 'second' }];

  it('returns the step declared under the id', () => {
    expect(requireStep(steps, 'second', 'Thing Evaluator')).toBe(steps[1]);
  });

  it('names the step it wanted and the evaluator whose contract lacks it', () => {
    expect(() => requireStep(steps, 'third', 'Thing Evaluator')).toThrow(
      'Step "third" not found in Thing Evaluator config.json',
    );
  });
});
