import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import {
  GradeLevelAppropriatenessEvaluator,
  readOutcome,
} from '../../src/index.js';

/**
 * The README's quickstart, run for real.
 *
 * It shipped `result.result.grade`, a field no schema has ever declared, so the first code
 * anyone ran returned `undefined`. A snippet nothing executes goes stale silently, so this
 * runs the documented call and checks the documented fields against the live response.
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';

if (RUN_INTEGRATION) {
  if (!process.env.GOOGLE_API_KEY) {
    throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
  }
}

const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

/** The exact text the README passes. */
const QUICKSTART_TEXT = "The cat's out of the bag now.";

describeIntegration('README quickstart', () => {
  it(
    'returns the fields the README prints',
    async () => {
      const evaluator = new GradeLevelAppropriatenessEvaluator({
        googleApiKey: process.env.GOOGLE_API_KEY,
      });

      const { result, metadata } = await evaluator.evaluate({ text: QUICKSTART_TEXT });

      // Every field the snippet reads has to exist and be populated — all three, not just
      // the first. `scaffolding_needed` is what makes the alternative band actionable, and
      // an empty string for any of them would render as a blank line in the documented
      // output while still typing as a string.
      expect(typeof result.grade_band).toBe('string');
      expect(result.grade_band).not.toBe('');
      expect(typeof result.alternative_grade_band).toBe('string');
      expect(result.alternative_grade_band).not.toBe('');
      expect(typeof result.scaffolding_needed).toBe('string');
      expect(result.scaffolding_needed).not.toBe('');
      expect(metadata.model).toMatch(/^google:/);

      // And the field it used to read must still not exist, so the old snippet cannot
      // quietly start "working" against a schema that never declared it.
      expect(result).not.toHaveProperty('grade');

      console.log(
        `  quickstart: grade_band=${result.grade_band} ` +
          `alternative=${result.alternative_grade_band} model=${metadata.model}\n` +
          `  scaffolding: ${result.scaffolding_needed}`,
      );
    },
    120_000,
  );

  it('prints a model string the README actually shows', async () => {
    const evaluator = new GradeLevelAppropriatenessEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY,
    });

    const { metadata } = await evaluator.evaluate({ text: QUICKSTART_TEXT });

    // The README comments a concrete model. A contract bump would leave it stale, and a
    // stale model string is how a reader concludes the SDK is not doing what it says.
    const readme = readFileSync(join(import.meta.dirname, '../../README.md'), 'utf-8');
    expect(readme).toContain(`// "${metadata.model}"`);
  }, 120_000);

  it('readOutcome reads the verdict the quickstart section describes', async () => {
    const evaluation = await new GradeLevelAppropriatenessEvaluator({
      googleApiKey: process.env.GOOGLE_API_KEY,
    }).evaluate({ text: QUICKSTART_TEXT });

    const { score, reasoning } = readOutcome(
      evaluation,
      GradeLevelAppropriatenessEvaluator.metadata.outcome,
    );

    expect(score).toBe(evaluation.result.grade_band);
    expect(reasoning.length).toBeGreaterThan(0);
  }, 120_000);
});
