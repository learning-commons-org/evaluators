import { describe, it, expect, vi, beforeEach } from 'vitest';
import { Provider, type BaseEvaluatorConfig } from '../../../src/evaluators/base.js';
import { GradeLevelAppropriatenessEvaluator } from '../../../src/evaluators/grade-level-appropriateness.js';
import { MeaningDirectnessEvaluator } from '../../../src/evaluators/meaning-directness.js';
import { BackgroundKnowledgeDemandsEvaluator } from '../../../src/evaluators/background-knowledge-demands.js';
import { SentenceStructureEvaluator } from '../../../src/evaluators/sentence-structure.js';
import { PurposeClarityEvaluator } from '../../../src/evaluators/purpose-clarity.js';
import { VocabularyComplexityEvaluator } from '../../../src/evaluators/vocabulary-complexity.js';

/**
 * Wiring only: every evaluator must accept an Anthropic override with just an
 * Anthropic key. Live behaviour is in anthropic-provider.integration.test.ts.
 */

// Hoisted for vi.mock's factory. The declared parameter is what types mock.calls.
const { createProvider } = vi.hoisted(() => {
  const mockProvider = {
    label: 'mock:model',
    generateStructured: vi.fn(),
    generateText: vi.fn(),
  };
  return {
    createProvider: vi.fn((_config: { type: string; model: string; apiKey?: string }) => mockProvider),
  };
});

vi.mock('../../../src/providers/index.js', async (importOriginal) => {
  const actual = await importOriginal();
  return { ...(actual as object), createProvider };
});

vi.mock('../../../src/telemetry/client.js', () => ({
  TelemetryClient: class {
    send = vi.fn().mockResolvedValue(undefined);
  },
}));

const ANTHROPIC_MODEL = 'claude-haiku-4-5-20251001';

function anthropicOnlyConfig(): BaseEvaluatorConfig {
  return {
    anthropicApiKey: 'sk-ant-test',
    modelOverride: { provider: Provider.Anthropic, model: ANTHROPIC_MODEL },
    telemetry: false,
  };
}

const EVALUATORS = [
  { name: 'GradeLevelAppropriateness', Ctor: GradeLevelAppropriatenessEvaluator },
  { name: 'Meaning Directness', Ctor: MeaningDirectnessEvaluator },
  { name: 'Background Knowledge Demands', Ctor: BackgroundKnowledgeDemandsEvaluator },
  { name: 'SentenceStructure', Ctor: SentenceStructureEvaluator },
  { name: 'Purpose', Ctor: PurposeClarityEvaluator },
  { name: 'Vocabulary', Ctor: VocabularyComplexityEvaluator },
] as const;

beforeEach(() => {
  vi.clearAllMocks();
});

describe('Anthropic modelOverride — plumbing', () => {
  for (const { name, Ctor } of EVALUATORS) {
    it(`${name} constructs with only an Anthropic key`, () => {
      expect(() => new Ctor(anthropicOnlyConfig())).not.toThrow();
      // The routing test below asserts the arguments; a `toHaveReturnedWith`
      // check here would be tautological, since the mock always returns it.
      expect(createProvider).toHaveBeenCalled();
    });

    it(`${name} routes every provider to Anthropic with the override model`, () => {
      new Ctor(anthropicOnlyConfig());

      expect(createProvider).toHaveBeenCalled();
      for (const [arg] of createProvider.mock.calls) {
        expect(arg.type).toBe(Provider.Anthropic);
        expect(arg.model).toBe(ANTHROPIC_MODEL);
        expect(arg.apiKey).toBe('sk-ant-test');
      }
    });
  }

  it('rejects an Anthropic override when the Anthropic key is missing', () => {
    expect(
      () =>
        new SentenceStructureEvaluator({
          openaiApiKey: 'sk-openai-test',
          modelOverride: { provider: Provider.Anthropic, model: ANTHROPIC_MODEL },
          telemetry: false,
        }),
    ).toThrow(/Missing required credential: anthropicApiKey/);
  });
});

describe('Anthropic modelOverride — vocabulary multi-model collapse', () => {
  // Vocabulary deliberately uses three models; an override collapses all three.
  // Asserted so the CLI can warn rather than surprise users.
  it('collapses all three vocabulary call sites onto the single override model', () => {
    new VocabularyComplexityEvaluator(anthropicOnlyConfig());

    expect(createProvider).toHaveBeenCalledTimes(3);
    const models = createProvider.mock.calls.map(([arg]) => arg.model);
    expect(models).toEqual([ANTHROPIC_MODEL, ANTHROPIC_MODEL, ANTHROPIC_MODEL]);
  });

  it('uses three distinct models across two providers without an override', () => {
    new VocabularyComplexityEvaluator({
      googleApiKey: 'g-test',
      openaiApiKey: 'o-test',
      telemetry: false,
    });

    const calls = createProvider.mock.calls.map(([arg]) => arg);
    expect(calls.map((c) => c.type)).toEqual([Provider.Google, Provider.OpenAI, Provider.OpenAI]);
    expect(new Set(calls.map((c) => c.model)).size).toBe(3);
  });
});
