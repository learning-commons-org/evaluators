import { describe, it, expect } from 'vitest';
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
} from '../../src/evaluators/academic-standards-alignment/mathematics/math-standards-alignment.js';

/**
 * Math Standards Alignment Evaluator Integration Tests
 *
 * Three cases across the 3.MD.C.7 family, chosen so the expected direction is unambiguous:
 *
 * - An L-shaped area question against `3.MD.C.7.d` (rectilinear decomposition), its
 *   canonical match.
 * - The same question against the parent `3.MD.C.7` (area by multiplication and addition).
 * - A bare arithmetic question against `3.MD.C.7.d`, which it should not align to at all.
 *
 * A standard's learning components come from the Knowledge Graph rather than from a model,
 * so they are asserted exactly. Whether a question aligns to one is the model's judgement
 * and moves between runs even at temperature 0 — for `3.MD.C.7.d` runs have produced 1, 2
 * and 3 of 3 — so alignment is asserted by direction and never by count.
 *
 * To run these tests:
 * ```bash
 * RUN_INTEGRATION_TESTS=true npm run test:integration
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
// A missing key when integration tests were explicitly requested is a
// misconfiguration, not a reason to quietly pass (matches batch/anthropic-provider).
if (RUN_INTEGRATION) {
  if (!process.env.ANTHROPIC_API_KEY) {
    throw new Error('ANTHROPIC_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  }
  if (!process.env.LEARNING_COMMONS_API_KEY) {
    throw new Error('LEARNING_COMMONS_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  }
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const TEST_TIMEOUT_MS = 2 * 60 * 1000;

const AREA_QUESTION =
  'A playground is shaped like an L. One part is a rectangle that is 8 feet long and 3 feet wide. ' +
  'Attached to it is another rectangle that is 4 feet long and 2 feet wide, with no overlap. ' +
  'What is the total area of the playground in square feet?';

interface TestCase {
  id: string;
  description: string;
  question: string;
  statement_code: string;
  /** The standard's learning components, in Knowledge Graph order. */
  components: string[];
  /** `some` = at least one component aligns; `none` = no component aligns. */
  alignment: 'some' | 'none';
}

const RECTILINEAR_COMPONENTS = [
  'Find the area of rectilinear figures by decomposing them into non-overlapping parts and finding the area of each part',
  'Find the area of rectilinear figures in real-world problems by decomposing them into non-overlapping parts and finding the area of each part',
  'Solve real-world problems involving rectilinear figures',
];

const TEST_CASES: TestCase[] = [
  {
    id: 'MSA1',
    description: 'L-shaped playground area against 3.MD.C.7.d',
    question: AREA_QUESTION,
    statement_code: '3.MD.C.7.d',
    components: RECTILINEAR_COMPONENTS,
    alignment: 'some',
  },
  {
    id: 'MSA2',
    description: 'simple addition against 3.MD.C.7.d',
    question: 'What is 12 + 7?',
    statement_code: '3.MD.C.7.d',
    components: RECTILINEAR_COMPONENTS,
    alignment: 'none',
  },
  {
    id: 'MSA3',
    description: 'L-shaped playground area against the parent standard 3.MD.C.7',
    question: AREA_QUESTION,
    statement_code: '3.MD.C.7',
    components: ['Use multiplication and addition to find the area of rectangles'],
    alignment: 'some',
  },
];

describeIntegration('MathStandardsAlignmentEvaluator - Integration', () => {
  it.each(TEST_CASES)(
    '$id: $description',
    async (testCase) => {
      const evaluator = new MathStandardsAlignmentEvaluator({
        anthropicApiKey: process.env.ANTHROPIC_API_KEY!,
        learningCommonsApiKey: process.env.LEARNING_COMMONS_API_KEY!,
      });

      const evaluation = await evaluator.evaluate({
        question: testCase.question,
        statement_code: testCase.statement_code,
        jurisdiction: Jurisdiction.MultiState,
      });
      const { result } = evaluation;

      expect(evaluation.evaluator).toBe(MathStandardsAlignmentEvaluator.metadata.id);
      expect(evaluation.metadata.model).toMatch(/^anthropic:/);
      expect(evaluation.metadata.processingTimeMs).toBeGreaterThan(0);
      expect(evaluation.metadata.processingTimeMs).toBeLessThan(10 * 60_000);
      // A live call consumes tokens, so a zero here means the envelope is reporting a
      // constant rather than what the run actually cost.
      expect(evaluation.metadata.tokenUsage.inputTokens).toBeGreaterThan(0);
      expect(evaluation.metadata.tokenUsage.outputTokens).toBeGreaterThan(0);

      console.log(`\n  ${testCase.id}: ${result.aligned_count}/${result.total_count} aligned`);
      for (const lc of result.learning_components) {
        console.log(`    ${lc.aligned ? '✓' : '✗'} ${lc.description.slice(0, 84)}`);
      }

      expect(result.statement_code).toBe(testCase.statement_code);
      expect(
        result.learning_components.map((lc) => lc.description),
        'learning components come from the Knowledge Graph, so they are exact',
      ).toEqual(testCase.components);
      expect(result.total_count).toBe(testCase.components.length);
      expect(result.aligned_count).toBe(
        result.learning_components.filter((lc) => lc.aligned).length,
      );

      if (testCase.alignment === 'none') {
        expect(
          result.aligned_count,
          `"${testCase.question.slice(0, 40)}…" must not align to ${testCase.statement_code}`,
        ).toBe(0);
      } else {
        expect(
          result.aligned_count,
          `"${testCase.question.slice(0, 40)}…" should align to ${testCase.statement_code}`,
        ).toBeGreaterThan(0);
      }

      // Every component is reasoned about, and a miss says how to fix the item — that is
      // the evaluator's actual product, and an empty string would satisfy the schema.
      for (const lc of result.learning_components) {
        expect(lc.reasoning.trim().length, `reasoning for "${lc.description}"`).toBeGreaterThan(20);
        if (!lc.aligned) {
          expect(
            lc.feedback?.trim().length ?? 0,
            `feedback for unaligned "${lc.description}"`,
          ).toBeGreaterThan(20);
        }
      }
    },
    TEST_TIMEOUT_MS,
  );
});
