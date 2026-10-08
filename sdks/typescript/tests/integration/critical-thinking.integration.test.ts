import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { describe, it, expect } from 'vitest';
import { CriticalThinkingEvaluator } from '../../src/evaluators/durable-skills/ela-writing/critical-thinking.js';
import { runEvaluatorTest, type BaseTestCase } from '../utils/index.js';

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

describeIntegration('CriticalThinkingEvaluator - Integration', () => {
  it('spans more than one score', () => {
    expect(new Set(TEST_CASES.map((testCase) => testCase.expected)).size).toBeGreaterThan(1);
  });

  it.each(TEST_CASES)(
    '$id expects $expected',
    async (testCase) => {
      const evaluator = new CriticalThinkingEvaluator({
        anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
        telemetry: false,
      });

      const result = await runEvaluatorTest(testCase, { evaluator });

      expect(result.matched, result.logs.join('\n')).toBe(true);
    },
    TEST_TIMEOUT_MS,
  );
});
