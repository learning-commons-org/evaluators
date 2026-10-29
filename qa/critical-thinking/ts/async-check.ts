/**
 * Scenario D7: three concurrent evaluations with Promise.all.
 *
 *   ./run.sh ts async inputs/B-one-passage.json      (three paid calls)
 */
import { readFileSync } from 'node:fs';
import { CriticalThinkingEvaluator, LogLevel } from '@learning-commons/evaluators';

if (!process.env.ANTHROPIC_API_KEY) {
  console.error('Set ANTHROPIC_API_KEY in your shell or in a .env file (here or at the repo root) first.');
  process.exit(2);
}

const { _note, ...inputs } = JSON.parse(readFileSync(process.argv[2], 'utf-8'));
const evaluator = new CriticalThinkingEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  telemetry: false,
  logLevel: LogLevel.SILENT,
});

const started = Date.now();
const results = await Promise.allSettled([1, 2, 3].map(() => evaluator.evaluate(inputs)));
const elapsed = (Date.now() - started) / 1000;

let failures = 0;
results.forEach((r, i) => {
  if (r.status === 'rejected') {
    failures++;
    console.log(`FAIL  call ${i + 1}: ${(r.reason as Error).name}: ${(r.reason as Error).message}`);
  } else {
    console.log(`PASS  call ${i + 1}: ${r.value.result.critical_thinking_score} (${r.value.metadata.processingTimeMs} ms)`);
  }
});
console.log(`      wall clock for all three: ${elapsed.toFixed(1)}s (should be close to one call, not three)`);
process.exitCode = failures ? 1 : 0;
