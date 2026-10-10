import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import CONFIG from '../../../../evals/graphics/ela/graphics-complexity/config.json';
import { GraphicsComplexityEvaluator, type GraphicsComplexityInput } from '../../src/evaluators/graphics/ela/graphics-complexity.js';

/**
 * Graphics Complexity integration tests: the contract's own fixtures, run for real.
 *
 * Each case is a row of `fixtures.json` — a passage, its grade, the images under `images/`
 * and their labels — with the rating it records as the expected result. This is the only
 * place the images-after-text request, the model-only response schema and the model's
 * behaviour are exercised together; the unit tests mock the provider.
 *
 * The contract's tolerance applies: a rating one rubric step from the expected one passes,
 * and `more_context_needed` has no neighbours. Each case retries up to three times.
 *
 * To run:
 * ```bash
 * RUN_INTEGRATION_TESTS=true GOOGLE_API_KEY=... npx vitest run tests/integration/graphics-complexity
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
if (RUN_INTEGRATION && !process.env.GOOGLE_API_KEY) {
  throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const CONTRACT_DIR = join(process.cwd(), '..', '..', 'evals/graphics/ela/graphics-complexity');
const TEST_TIMEOUT_MS = 4 * 60 * 1000;
const ATTEMPTS = 3;
const RUBRIC = ['slightly_complex', 'moderately_complex', 'very_complex', 'exceedingly_complex'];

interface Fixture {
  id: string;
  description: string;
  input: GraphicsComplexityInput;
  expected: { complexity_score: string };
}

const FIXTURES: Fixture[] = JSON.parse(readFileSync(join(CONTRACT_DIR, 'fixtures.json'), 'utf-8'));

function withinTolerance(actual: string, expected: string): boolean {
  if (actual === expected) return true;
  if (!CONFIG.fixtures.tolerance.allow_adjacent_levels) return false;
  const a = RUBRIC.indexOf(actual);
  const e = RUBRIC.indexOf(expected);
  return a !== -1 && e !== -1 && Math.abs(a - e) === 1;
}

describeIntegration('GraphicsComplexityEvaluator — contract fixtures, real calls', () => {
  it('has fixtures to run, so nothing below passes vacuously', () => {
    expect(FIXTURES.length).toBeGreaterThan(0);
  });

  it.each(FIXTURES)('$id — $description', async (fixture) => {
    const evaluator = new GraphicsComplexityEvaluator({ googleApiKey: process.env.GOOGLE_API_KEY!, telemetry: false });
    const input = { ...fixture.input, image_paths: fixture.input.image_paths.map((p) => join(CONTRACT_DIR, p)) };
    const seen: string[] = [];

    for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
      const { result, metadata } = await evaluator.evaluate(input);
      seen.push(result.complexity_score);

      expect(Object.keys(result).sort()).toEqual(['complexity_score', 'details', 'reasoning']);
      expect(metadata.model).toBe(`${CONFIG.steps[0].model.provider}:${CONFIG.steps[0].model.name}`);

      if (withinTolerance(result.complexity_score, fixture.expected.complexity_score)) return;
    }

    expect.fail(`${fixture.id}: expected ${fixture.expected.complexity_score} (±1) in ${ATTEMPTS} attempts; saw ${seen.join(', ')}`);
  }, TEST_TIMEOUT_MS);
});
