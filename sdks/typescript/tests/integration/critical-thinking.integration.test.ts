import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, it, expect } from 'vitest';
import CONFIG from '../../../../evals/durable-skills/ela-writing/critical-thinking/config.json';
import { CriticalThinkingEvaluator } from '../../src/evaluators/durable-skills/ela-writing/critical-thinking.js';
import type { EvaluationResult } from '../../src/schemas/index.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';
import { medianRating, presentRatings } from '../unit/evaluators/critical-thinking-score.test.js';

/**
 * Critical Thinking evaluator integration tests.
 *
 * Cases are this evaluator's `fixtures.json`. `critical_thinking_score` is the expected
 * verdict. A neighboring level on not_evident < exploring < analyzing < integrating <
 * extending is acceptable, which is the contract's `allow_adjacent_levels` rule.
 *
 * Anthropic is the provider this contract names, and CI does not supply that key, so a
 * missing key skips the suite.
 *
 * ```bash
 * ANTHROPIC_API_KEY=... RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
const describeIntegration =
  RUN_INTEGRATION && process.env.ANTHROPIC_API_KEY ? describe : describe.skip;

const TEST_TIMEOUT_MS = 3 * 60 * 1000;

const LEVELS = ['not_evident', 'exploring', 'analyzing', 'integrating', 'extending'] as const;

interface Fixture {
  id: string;
  input: {
    assignment_text: string;
    source_passages: Array<{ title?: string; author?: string; text: string }>;
    essay_text: string;
  };
  expected: { critical_thinking_score: (typeof LEVELS)[number] };
}

const FIXTURES = JSON.parse(
  readFileSync(
    join(
      import.meta.dirname,
      '../../../../evals/durable-skills/ela-writing/critical-thinking/fixtures.json',
    ),
    'utf-8',
  ),
) as Fixture[];

function neighbors(level: (typeof LEVELS)[number]): string[] {
  const index = LEVELS.indexOf(level);
  return [LEVELS[index - 1], LEVELS[index + 1]].filter((item): item is (typeof LEVELS)[number] =>
    item !== undefined,
  );
}

const TEST_CASES: BaseTestCase[] = FIXTURES.map((fixture) => ({
  id: fixture.id,
  inputs: fixture.input,
  expected: fixture.expected.critical_thinking_score,
  acceptable: neighbors(fixture.expected.critical_thinking_score),
}));

// Three long passages are the expensive call. The case stays in fixtures.json.
const LIVE_CASES = TEST_CASES.filter((testCase) => testCase.id !== '5076429_cleaned');

describeIntegration('CriticalThinkingEvaluator - Integration', () => {
  it('spans more than one score', () => {
    expect(new Set(TEST_CASES.map((testCase) => testCase.expected)).size).toBeGreaterThan(1);
  });

  it.each(LIVE_CASES)(
    '$id expects $expected',
    async (testCase) => {
      const evaluator = new CriticalThinkingEvaluator({
        anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, {
        evaluator,
        extractResult: (evaluation: EvaluationResult<Record<string, unknown>>) => {
          const payload = evaluation.result as {
            critical_thinking_score: string;
            indicators: Record<string, { rating: string } | undefined>;
          };
          const score = payload.critical_thinking_score;
          expect(score).toBe(medianRating(presentRatings(payload.indicators)));
          return score;
        },
      });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );

  // Four short passages, once. The three-passage fixture stays out of this run, so this
  // call is what still rates indicator 2.1 and checks the five-rating median.
  it(
    'rates four short passages in one call',
    async () => {
      const evaluator = new CriticalThinkingEvaluator({
        anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
        telemetry: false,
      });

      const evaluation = await evaluator.evaluate({
        assignment_text: 'Argue whether towns should plant more street trees. Use the sources.',
        source_passages: [
          {
            title: 'Shade',
            author: 'City trees office',
            text: 'Street trees cool sidewalks and give birds a place to nest.',
          },
          {
            title: 'Roots',
            author: null,
            text: 'Tree roots can lift pavement when they are planted in a narrow strip.',
          },
          {
            author: 'A gardener',
            text: 'Young trees need water through their first summer.',
          },
          { text: 'Bare soil dries faster when nothing shades it.' },
        ],
        essay_text:
          'Towns should plant more street trees. Shade says they cool sidewalks. ' +
          'Roots warns that pavement can lift, so each tree needs room. ' +
          'A gardener says young trees need water. Bare soil dries faster without shade.',
      });

      expect(evaluation.evaluator).toBe(CONFIG.evaluator.id);
      const model = CONFIG.steps[0].model;
      expect(evaluation.metadata.model).toBe(`${model.provider}:${model.name}`);
      const score = evaluation.result.critical_thinking_score;
      expect(LEVELS).toContain(score);
      expect(score).toBe(
        medianRating(
          presentRatings(
            evaluation.result.indicators as Record<string, { rating: string } | undefined>,
          ),
        ),
      );
    },
    TEST_TIMEOUT_MS,
  );
});
