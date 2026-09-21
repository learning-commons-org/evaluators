import { describe, it, expect, vi, beforeEach } from 'vitest';
import { readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { RateLimitError } from '../../../src/errors.js';
import { Provider, type BaseEvaluatorConfig } from '../../../src/evaluators/base.js';
import { configFieldFor } from '../../../src/evaluators/credentials.js';
import { PurposeClarityEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/purpose-clarity.js';
import { SentenceStructureEvaluator } from '../../../src/evaluators/text-complexity/ela-reading/sentence-structure.js';

/**
 * The cross-SDK telemetry oracle.
 *
 * Both SDKs' events land in one collector and are aggregated together, so this SDK's
 * events are the reference the Python SDK is checked against. Each case below is run here
 * with a stubbed provider, and the event it produces is written to
 * `tests/fixtures/telemetry-events.json` alongside the inputs that produced it;
 * `sdks/python/tests/unit/telemetry/test_cross_sdk_events.py` replays the same cases and
 * compares its own events to that file.
 *
 * So this test fails when this SDK's events change, which is the point: the recorded file
 * is the contract, and regenerating it (`UPDATE_TELEMETRY_ORACLE=1 npm run test:unit`)
 * commits both SDKs to the change.
 *
 * Only what a run cannot repeat is masked — the clock, the wall-clock latency, and
 * `sdk_version`, which each SDK reports as itself.
 */

/** What every stubbed model call reports, so an event's numbers are the same in both SDKs. */
const USAGE = { inputTokens: 250, outputTokens: 120 };
const STAGE_LATENCY_MS = 900;

/**
 * One answer for every step of every case: the sentence-analysis counts a later step's
 * preprocessing reads, plus the verdict an evaluator's own output carries. No event carries
 * a model's output, so the two SDKs need only stub something their steps can consume — this
 * one, and schema-derived samples on the Python side.
 */
const STEP_OUTPUT = {
  complexity_score: 'moderately_complex',
  reasoning: 'stub',
  num_sentences: 2,
  num_words: 10,
  flesch_kincaid_grade: 3.5,
  num_simple_sentences: 2,
  num_compound_sentences: 0,
  num_complex_sentences: 0,
  num_compound_complex_sentences: 0,
  num_other_sentences: 0,
  num_independent_clauses: 2,
  num_subordinate_clauses: 0,
  num_total_clauses: 2,
  num_sentences_with_subordinate: 0,
  num_sentences_with_multiple_subordinates: 0,
  num_sentences_with_embedded_clauses: 0,
  num_prepositional_phrases: 1,
  num_participle_phrases: 0,
  num_appositive_phrases: 0,
  num_simple_transitions: 0,
  num_sophisticated_transitions: 0,
  words_in_simple_sentences: 10,
  words_in_compound_sentences: 0,
  words_in_complex_sentences: 0,
  words_in_compound_complex_sentences: 0,
  words_in_other_sentences: 0,
  sentence_word_counts: [5, 5],
  num_one_concept_sentences: 2,
  num_multi_concept_sentences: 0,
  num_cleft_sentences: 0,
  max_clauses_in_any_sentence: 1,
  num_compound: 0,
  num_basic_complex: 0,
  num_advanced_complex: 0,
  percentage_simple: 100,
  percentage_compound: 0,
  percentage_basic_complex: 0,
  percentage_advanced_complex: 0,
};

const MASK = '<masked>';

const TEXT =
  'When going to the beach, find out which ones have lifeguards. Rip currents are like ' +
  'fast-flowing rivers that can pull even strong swimmers away from the beach.';

interface Case {
  /** Name the Python side reports too, so a failure names the same case in both suites. */
  id: string;
  /** Registry id, which is how the Python side finds the same evaluator. */
  evaluator: string;
  inputs: Record<string, string>;
  /** Applied as `modelOverride` here and `model_override` there. */
  model_override?: { provider: string; model: string };
  /** A `RateLimitError` from the provider on this call, 1-based. */
  fail_at_call?: number;
  /** Whether the evaluation is expected to raise. */
  raises?: boolean;
}

const CASES: Case[] = [
  {
    id: 'single-step/success',
    evaluator: 'text_complexity.ela_reading.purpose_clarity',
    inputs: { text: TEXT, grade_level: '5' },
  },
  {
    id: 'single-step/rejected-input',
    evaluator: 'text_complexity.ela_reading.purpose_clarity',
    // A grade outside the contract's enum: the failure happens inside the error boundary,
    // so it is telemetered like any other.
    inputs: { text: TEXT, grade_level: '2' },
    raises: true,
  },
  {
    id: 'single-step/provider-failure',
    evaluator: 'text_complexity.ela_reading.purpose_clarity',
    inputs: { text: TEXT, grade_level: '5' },
    fail_at_call: 1,
    raises: true,
  },
  {
    id: 'single-step/model-override',
    evaluator: 'text_complexity.ela_reading.purpose_clarity',
    inputs: { text: TEXT, grade_level: '5' },
    model_override: { provider: 'anthropic', model: 'claude-opus-5' },
  },
  {
    id: 'multi-step/success',
    evaluator: 'text_complexity.ela_reading.sentence_structure',
    inputs: { text: TEXT, grade_level: '5' },
  },
  {
    id: 'multi-step/failure-after-one-step',
    evaluator: 'text_complexity.ela_reading.sentence_structure',
    inputs: { text: TEXT, grade_level: '5' },
    fail_at_call: 2,
    raises: true,
  },
];

const EVALUATORS = {
  'text_complexity.ela_reading.purpose_clarity': PurposeClarityEvaluator,
  'text_complexity.ela_reading.sentence_structure': SentenceStructureEvaluator,
} as const;

const sent: Record<string, unknown>[] = [];
let calls = 0;
let failAtCall: number | null = null;

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = async (event: Record<string, unknown>): Promise<void> => {
      sent.push(event);
    };
  },
}));

// Labelled `provider:model` from the config the contract produced, so the events carry the
// models the contracts declare rather than a placeholder both SDKs would agree on trivially.
vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    createProvider: vi.fn((config: { type: string; model: string }) => ({
      label: `${config.type}:${config.model}`,
      generateStructured: vi.fn(async () => {
        calls += 1;
        if (failAtCall === calls) {
          throw new RateLimitError('slow down', { dependency: 'openai' });
        }
        return {
          data: STEP_OUTPUT,
          model: config.model,
          usage: USAGE,
          latencyMs: STAGE_LATENCY_MS,
        };
      }),
      generateText: vi.fn(),
    })),
  };
});

/** The event with the values a second run could not reproduce replaced. */
function normalize(event: Record<string, unknown>): Record<string, unknown> {
  return { ...event, timestamp: MASK, sdk_version: MASK, latency_ms: MASK };
}

function configFor(testCase: Case): BaseEvaluatorConfig {
  const evaluator = EVALUATORS[testCase.evaluator as keyof typeof EVALUATORS];
  const providers = testCase.model_override
    ? [testCase.model_override.provider]
    : evaluator.metadata.defaultProviders;
  const config: Record<string, unknown> = {};
  for (const provider of providers) {
    config[configFieldFor(`${provider}_api_key`)] = 'test-key';
  }
  if (testCase.model_override) {
    config.modelOverride = {
      provider: testCase.model_override.provider as Provider,
      model: testCase.model_override.model,
    };
  }
  return config as BaseEvaluatorConfig;
}

async function eventFor(testCase: Case): Promise<Record<string, unknown>> {
  sent.length = 0;
  calls = 0;
  failAtCall = testCase.fail_at_call ?? null;

  const Evaluator = EVALUATORS[testCase.evaluator as keyof typeof EVALUATORS];
  const evaluator = new Evaluator(configFor(testCase));
  await expect(evaluator.evaluate(testCase.inputs as never))[
    testCase.raises ? 'rejects' : 'resolves'
  ].toBeDefined();

  expect(sent, `${testCase.id}: one event per evaluation`).toHaveLength(1);
  return normalize(sent[0]);
}

const ORACLE = join(
  dirname(fileURLToPath(import.meta.url)),
  '../../fixtures/telemetry-events.json',
);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('the events this SDK emits are the cross-SDK oracle', () => {
  it('emits what the recorded oracle holds, case for case', async () => {
    const captured = [];
    for (const testCase of CASES) {
      captured.push({ ...testCase, event: await eventFor(testCase) });
    }

    if (process.env.UPDATE_TELEMETRY_ORACLE) {
      writeFileSync(ORACLE, `${JSON.stringify(captured, null, 2)}\n`);
    }

    expect(captured).toEqual(JSON.parse(readFileSync(ORACLE, 'utf-8')));
  });
});
