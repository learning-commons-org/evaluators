import { describe, it, expect } from 'vitest';
import { readFileSync } from 'node:fs';
import { join } from 'node:path';
import { GraphicsAccuracyEvaluator } from '../../src/evaluators/academic-standards-alignment/mathematics/graphics-accuracy.js';

/**
 * Graphics Accuracy integration tests: the contract's own fixtures, run for real.
 *
 * Each case is a row of `fixtures.json` — an image under `images/` plus the claim the
 * evaluator receives — with the verdict it records as the expected result. This is the only
 * place the image path, the provider's multimodal request and the model's behaviour are
 * exercised together; the unit tests mock the provider.
 *
 * `is_correct` is asserted strictly. `basis` is asserted only when the fixture expects
 * `supported`: a false verdict can legitimately arrive as `contradicted` or `unverified`
 * depending on how far the model's derivation got, and the fixtures record the more common
 * of the two, not the only acceptable one. Each case retries up to three times, since a
 * single call can land on the wrong side of a hard item.
 *
 * To run:
 * ```bash
 * RUN_INTEGRATION_TESTS=true GOOGLE_API_KEY=... npx vitest run tests/integration/graphics-accuracy
 * ```
 */

const RUN_INTEGRATION = process.env.RUN_INTEGRATION_TESTS === 'true';
if (RUN_INTEGRATION && !process.env.GOOGLE_API_KEY) {
  throw new Error('GOOGLE_API_KEY is required when RUN_INTEGRATION_TESTS=true');
}
const describeIntegration = RUN_INTEGRATION ? describe : describe.skip;

const CONTRACT_DIR = join(process.cwd(), '..', '..', 'evals/academic-standards-alignment/mathematics/graphics-accuracy');
const TEST_TIMEOUT_MS = 4 * 60 * 1000;
const ATTEMPTS = 3;

interface Fixture {
  id: string;
  description: string;
  input: { image: string; claim: string };
  expected: { is_correct: boolean; basis: 'supported' | 'contradicted' | 'unverified' };
}

const FIXTURES: Fixture[] = JSON.parse(readFileSync(join(CONTRACT_DIR, 'fixtures.json'), 'utf-8'));

describeIntegration('GraphicsAccuracyEvaluator — contract fixtures, real calls', () => {
  const evaluator = new GraphicsAccuracyEvaluator({ googleApiKey: process.env.GOOGLE_API_KEY!, telemetry: false });

  it('has fixtures to run, so nothing below passes vacuously', () => {
    expect(FIXTURES.length).toBeGreaterThan(0);
  });

  it.each(FIXTURES)('$id — $description', async (fixture) => {
    const image = join(CONTRACT_DIR, fixture.input.image);
    const seen: Array<{ is_correct: boolean; basis: string; correction: string }> = [];

    for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
      const { result, metadata } = await evaluator.evaluate({ image, claim: fixture.input.claim });
      seen.push({ is_correct: result.is_correct, basis: result.basis, correction: result.correction });

      // The paper's mandated sentence is what makes the verdict auditable; every parsed
      // response must carry it.
      expect(result.analysis, `${fixture.id}: X-vs-Y sentence`).toMatch(/The image yields .*the specification states .*therefore is_correct/is);
      expect(metadata.model).toBe('google:gemini-3.6-flash');

      const verdictOk = result.is_correct === fixture.expected.is_correct;
      const basisOk = fixture.expected.basis !== 'supported' || result.basis === 'supported';
      if (verdictOk && basisOk) return;
    }

    expect.fail(`${fixture.id}: expected is_correct=${fixture.expected.is_correct} (${fixture.expected.basis}) in ${ATTEMPTS} attempts; saw ${JSON.stringify(seen)}`);
  }, TEST_TIMEOUT_MS);
});
