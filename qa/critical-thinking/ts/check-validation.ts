/**
 * Scenario D5: run every case in validation_cases.json and report PASS/FAIL.
 *
 * Uses a dummy key, so no paid calls. Validation runs before the model is contacted; a case
 * that passes validation then fails with AuthenticationError, which counts as "accepted".
 *
 *   ./run.sh ts validate
 */
import { readFileSync } from 'node:fs';
import { CriticalThinkingEvaluator, LogLevel } from '@learning-commons/evaluators';

type Json = unknown;

function expand(value: Json): Json {
  if (Array.isArray(value)) return value.map(expand);
  if (value && typeof value === 'object') {
    const obj = value as Record<string, Json>;
    if ('$repeat' in obj) {
      const [char, n] = obj.$repeat as [string, number];
      return char.repeat(n);
    }
    return Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, expand(v)]));
  }
  return value;
}

interface Case {
  id: string;
  desc: string;
  set?: Record<string, Json>;
  unset?: string[];
  expect_error: string | null;
  message?: string;
}

const spec = JSON.parse(readFileSync(process.argv[2], 'utf-8')) as { base: Record<string, Json>; cases: Case[] };

const evaluator = new CriticalThinkingEvaluator({
  anthropicApiKey: 'sk-ant-qa-dummy-key',
  telemetry: false,
  maxRetries: 0,
  logLevel: LogLevel.SILENT,
});

let failures = 0;
for (const c of spec.cases) {
  const inputs: Record<string, Json> = { ...structuredClone(spec.base), ...(expand(c.set ?? {}) as object) };
  for (const key of c.unset ?? []) delete inputs[key];

  let gotClass: string | null = null;
  let gotMessage = '';
  try {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    await evaluator.evaluate(inputs as any);
  } catch (error) {
    gotClass = (error as Error).name;
    gotMessage = (error as Error).message;
  }

  const ok =
    c.expect_error === null
      ? gotClass === null || gotClass === 'AuthenticationError'
      : gotClass === c.expect_error && gotMessage === c.message;
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${c.id}  ${c.desc}`);
  if (!ok) {
    console.log(`      expected: ${c.expect_error}: ${c.message ?? '(accepted)'}`);
    console.log(`      got:      ${gotClass}: ${gotMessage}`);
  }
}

console.log(`\n${spec.cases.length - failures}/${spec.cases.length} passed`);
process.exitCode = failures ? 1 : 0;
