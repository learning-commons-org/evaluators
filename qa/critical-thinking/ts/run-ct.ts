/**
 * Run the Critical Thinking evaluator on one input file and print the result.
 *
 * From qa/critical-thinking:
 *   export ANTHROPIC_API_KEY=...   # or put it in .env
 *   ./run.sh ts inputs/A-three-passages-mixed.json
 *   ./run.sh ts inputs/B-one-passage.json --spy-telemetry
 *   ./run.sh ts inputs/B-one-passage.json --no-telemetry
 *
 * The SDK never reads keys from the environment; this script does, and passes the key in.
 * Each run is one paid model call (roughly $0.03-$0.19 depending on input size).
 */
import { readFileSync } from 'node:fs';
import { CriticalThinkingEvaluator, LogLevel } from '@learning-commons/evaluators';

const LEVELS = ['not_evident', 'exploring', 'analyzing', 'integrating', 'extending'];

/** Median on LEVELS order, rounding up on an even count (prompt rule 6). */
function medianRating(ratings: string[]): string {
  const ordered = ratings.map((r) => LEVELS.indexOf(r)).sort((a, b) => a - b);
  return LEVELS[ordered[Math.floor(ordered.length / 2)]];
}

const args = process.argv.slice(2);
const file = args.find((a) => !a.startsWith('--'));
const spy = args.includes('--spy-telemetry');
const noTelemetry = args.includes('--no-telemetry');

if (!file || !process.env.ANTHROPIC_API_KEY) {
  console.error('Usage: ./run.sh ts <input.json> [--spy-telemetry|--no-telemetry]. Set ANTHROPIC_API_KEY in your shell or in a .env file (here or at the repo root) first.');
  process.exit(2);
}

if (spy) {
  // The SDK posts telemetry with the global fetch; print those bodies before sending.
  const realFetch = globalThis.fetch;
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    const url = input instanceof Request ? input.url : String(input);
    if (url.includes('evaluators-telemetry')) console.error(`[telemetry] ${String(init?.body)}`);
    return realFetch(input, init);
  };
}

const { _note, ...inputs } = JSON.parse(readFileSync(file, 'utf-8'));

const evaluator = new CriticalThinkingEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  telemetry: !noTelemetry,
  logLevel: LogLevel.SILENT,
});

try {
  const evaluation = await evaluator.evaluate(inputs);
  const json = JSON.stringify(evaluation, null, 2);
  console.log(json);

  const indicators = JSON.parse(json).result.indicators as Record<string, { rating: string } | null>;
  const ratings = Object.values(indicators).filter(Boolean).map((v) => v!.rating);
  const score = evaluation.result.critical_thinking_score;
  const synth = !('synthesizing_sources' in indicators)
    ? 'absent'
    : indicators.synthesizing_sources ? 'present' : 'present as null (bug?)';

  console.log('\n--- summary ---');
  console.log(`passages:               ${inputs.source_passages?.length ?? 0}`);
  console.log(`indicators rated:       ${Object.keys(indicators).join(', ')}`);
  console.log(`synthesizing_sources:   ${synth}`);
  console.log(`score:                  ${score}`);
  console.log(`score == median:        ${score === medianRating(ratings)}`);
  console.log(`tokens in / out:        ${evaluation.metadata.tokenUsage.inputTokens} / ${evaluation.metadata.tokenUsage.outputTokens}`);
  console.log(`time:                   ${evaluation.metadata.processingTimeMs} ms`);
} catch (error) {
  console.log(`${(error as Error).name}: ${(error as Error).message}`);
  process.exitCode = 1;
}
