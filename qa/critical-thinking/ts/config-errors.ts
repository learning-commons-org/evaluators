/**
 * Scenario D6: configuration and provider errors. Makes no billable calls.
 *
 * 1. No key                    -> ConfigurationError at construction, before any I/O
 * 2. Invalid key               -> AuthenticationError, retryable false
 * 3. Model that doesn't exist  -> ConfigurationError (needs ANTHROPIC_API_KEY; the call is refused)
 */
import { readFileSync } from 'node:fs';
import { CriticalThinkingEvaluator, LogLevel, Provider } from '@learning-commons/evaluators';

const { _note, ...inputs } = JSON.parse(
  readFileSync(new URL('../inputs/B-one-passage.json', import.meta.url), 'utf-8'),
);
let failures = 0;

async function check(name: string, expected: string, fn: () => unknown): Promise<void> {
  let got: string | null = null;
  let detail = 'no error';
  try {
    await fn();
  } catch (error) {
    got = (error as Error).name;
    detail = (error as Error).message;
    const retryable = (error as { retryable?: boolean }).retryable;
    if (retryable !== undefined) detail += ` (retryable=${retryable})`;
  }
  const ok = got === expected;
  if (!ok) failures++;
  console.log(`${ok ? 'PASS' : 'FAIL'}  ${name}\n      expected ${expected}; got ${got}: ${detail}`);
}

await check('1. no key', 'ConfigurationError', () =>
  new CriticalThinkingEvaluator({ telemetry: false, logLevel: LogLevel.SILENT }),
);

await check('2. invalid key', 'AuthenticationError', () =>
  new CriticalThinkingEvaluator({
    anthropicApiKey: 'sk-ant-qa-invalid',
    telemetry: false,
    maxRetries: 0,
    logLevel: LogLevel.SILENT,
  }).evaluate(inputs),
);

const key = process.env.ANTHROPIC_API_KEY;
if (!key) {
  console.log('SKIP  3. unknown model (set ANTHROPIC_API_KEY in your shell or .env to run it)');
} else {
  await check('3. unknown model', 'ConfigurationError', () =>
    new CriticalThinkingEvaluator({
      anthropicApiKey: key,
      telemetry: false,
      maxRetries: 0,
      logLevel: LogLevel.SILENT,
      modelOverride: { provider: Provider.Anthropic, model: 'claude-qa-does-not-exist' },
    }).evaluate(inputs),
  );
}

process.exitCode = failures ? 1 : 0;
