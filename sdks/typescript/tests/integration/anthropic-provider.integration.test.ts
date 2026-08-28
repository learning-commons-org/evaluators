import { describe, it, expect } from 'vitest';
import { Provider, type BaseEvaluatorConfig } from '../../src/evaluators/base.js';
import type { EvaluationResult } from '../../src/schemas/index.js';
import { GradeLevelAppropriatenessEvaluator } from '../../src/evaluators/grade-level-appropriateness.js';
import { MeaningDirectnessEvaluator } from '../../src/evaluators/meaning-directness.js';
import { BackgroundKnowledgeDemandsEvaluator } from '../../src/evaluators/background-knowledge-demands.js';
import { SentenceStructureEvaluator } from '../../src/evaluators/sentence-structure.js';
import { PurposeClarityEvaluator } from '../../src/evaluators/purpose-clarity.js';
import { VocabularyComplexityEvaluator } from '../../src/evaluators/vocabulary-complexity.js';

/**
 * Anthropic provider integration tests (live API). Structured output on Anthropic is
 * tool-call based, so only a live call proves the larger nested schemas round-trip.
 * Verifies the provider works, not evaluation quality.
 *
 * `ANTHROPIC_API_KEY=... RUN_INTEGRATION_TESTS=true npm run test:integration`
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';

// Anthropic is an *optional* provider: no evaluator defaults to it, and CI
// supplies only OPENAI/GOOGLE. So a missing key skips this suite rather than
// failing a run that has keys for every other one — unlike the suites whose
// provider key is required, which throw. Same policy as the optional keys in
// math-standards-alignment.integration.test.ts.
const describeIntegration =
  RUN_INTEGRATION && process.env.ANTHROPIC_API_KEY ? describe : describe.skip;

const TEST_TIMEOUT_MS = 3 * 60 * 1000;
const ANTHROPIC_MODEL = process.env.ANTHROPIC_TEST_MODEL ?? 'claude-haiku-4-5-20251001';
const GRADE = '5';

const SAMPLE_TEXT =
  'The water cycle describes how water moves around our planet. When the sun heats lakes and ' +
  'oceans, some water turns into vapour and rises into the air. High above the ground it cools ' +
  'and forms clouds. Eventually the droplets grow heavy and fall back down as rain or snow, and ' +
  'the cycle begins again.';

function anthropicConfig(): BaseEvaluatorConfig {
  return {
    anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
    modelOverride: { provider: Provider.Anthropic, model: ANTHROPIC_MODEL },
    telemetry: false,
  };
}

/** Per-entry `run` so each evaluator is called with its real arity — GLA takes only `text`. */
const EVALUATORS: Array<{
  name: string;
  run: (config: BaseEvaluatorConfig) => Promise<EvaluationResult<string, unknown>>;
}> = [
  {
    name: 'GradeLevelAppropriateness',
    run: (c) => new GradeLevelAppropriatenessEvaluator(c).evaluate(SAMPLE_TEXT),
  },
  { name: 'Meaning Directness', run: (c) => new MeaningDirectnessEvaluator(c).evaluate(SAMPLE_TEXT, GRADE) },
  { name: 'Background Knowledge Demands', run: (c) => new BackgroundKnowledgeDemandsEvaluator(c).evaluate(SAMPLE_TEXT, GRADE) },
  { name: 'SentenceStructure', run: (c) => new SentenceStructureEvaluator(c).evaluate(SAMPLE_TEXT, GRADE) },
  { name: 'Purpose', run: (c) => new PurposeClarityEvaluator(c).evaluate(SAMPLE_TEXT, GRADE) },
  { name: 'Vocabulary', run: (c) => new VocabularyComplexityEvaluator(c).evaluate(SAMPLE_TEXT, GRADE) },
];

describeIntegration('Anthropic provider — all text-complexity evaluators (live API)', () => {
  for (const { name, run } of EVALUATORS) {
    it(
      `${name} completes on Anthropic and returns a structured result`,
      async () => {
        const result = await run(anthropicConfig());

        expect(result.score).toBeDefined();
        expect(typeof result.score).toBe('string');
        expect((result.score as string).length).toBeGreaterThan(0);
        expect(typeof result.reasoning).toBe('string');
        expect(result.metadata.model).toContain('anthropic');
        expect(result.metadata.model).toContain(ANTHROPIC_MODEL);
      },
      TEST_TIMEOUT_MS,
    );
  }
});
