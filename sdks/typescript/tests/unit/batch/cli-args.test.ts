import { describe, it, expect } from 'vitest';
import { parseArgs, parseModelOverride, requiredProviders } from '../../../src/batch/cli-args.js';
import { Provider } from '../../../src/batch/index.js';
import type { EvaluatorGroup } from '../../../src/batch/index.js';

// ---- parseModelOverride ----

describe('parseModelOverride', () => {
  it('parses a valid provider:model string', () => {
    expect(parseModelOverride('anthropic:claude-opus-4-8')).toEqual({
      provider: Provider.Anthropic,
      model: 'claude-opus-4-8',
    });
  });

  it('lowercases the provider', () => {
    expect(parseModelOverride('ANTHROPIC:claude-opus-4-8').provider).toBe(Provider.Anthropic);
    expect(parseModelOverride('OpenAI:gpt-4o').provider).toBe(Provider.OpenAI);
  });

  it('preserves colons inside the model name', () => {
    expect(parseModelOverride('openai:gpt-4:turbo')).toEqual({
      provider: Provider.OpenAI,
      model: 'gpt-4:turbo',
    });
  });

  it('throws when no colon is present', () => {
    expect(() => parseModelOverride('anthropicmodel')).toThrow('provider:model');
  });

  it('throws for an unknown provider', () => {
    expect(() => parseModelOverride('bedrock:model')).toThrow('Unknown provider "bedrock"');
  });

  it('throws when the model name is empty', () => {
    expect(() => parseModelOverride('anthropic:')).toThrow('Model name cannot be empty');
  });

  it('throws when the model name is only whitespace', () => {
    expect(() => parseModelOverride('anthropic:   ')).toThrow('Model name cannot be empty');
  });

  it('accepts all three valid providers', () => {
    expect(() => parseModelOverride('google:gemini-2.5-pro')).not.toThrow();
    expect(() => parseModelOverride('openai:gpt-4o')).not.toThrow();
    expect(() => parseModelOverride('anthropic:claude-opus-4-8')).not.toThrow();
  });

  it('trims whitespace from the provider (symmetric with model trim)', () => {
    expect(parseModelOverride(' anthropic :claude-opus-4-8')).toEqual({
      provider: Provider.Anthropic,
      model: 'claude-opus-4-8',
    });
  });
});

// ---- parseArgs ----

describe('parseArgs', () => {
  it('returns empty object for no args', () => {
    expect(parseArgs([])).toEqual({});
  });

  it('captures the first non-flag argument as csv', () => {
    expect(parseArgs(['input.csv'])).toMatchObject({ csvPath: 'input.csv' });
  });

  it('captures an empty positional as csv so the caller gets a clear file-not-found error', () => {
    // parseArgs should not swallow ''; the CLI path (parseCSV) gives the user a clear error
    expect(parseArgs([''])).toMatchObject({ csvPath: '' });
  });

  it('ignores a second positional argument', () => {
    expect(parseArgs(['a.csv', 'b.csv'])).toMatchObject({ csvPath: 'a.csv' });
  });

  it('an empty first positional locks in csv so a later positional cannot overwrite it', () => {
    // Ensures the undefined check (not falsiness) is used — '' should hold its place
    expect(parseArgs(['', 'input.csv'])).toMatchObject({ csvPath: '' });
  });

  it('does not treat a value arg as the csv path', () => {
    // '3' is the value of --concurrency, not a positional csv
    const result = parseArgs(['--concurrency', '3', 'input.csv']);
    expect(result.csvPath).toBe('input.csv');
    expect(result.concurrency).toBe(3);
  });

  it('parses --help and -h', () => {
    expect(parseArgs(['--help'])).toMatchObject({ help: true });
    expect(parseArgs(['-h'])).toMatchObject({ help: true });
  });

  it('parses --version', () => {
    expect(parseArgs(['--version'])).toMatchObject({ version: true });
  });

  it('parses --no-telemetry', () => {
    expect(parseArgs(['--no-telemetry'])).toMatchObject({ noTelemetry: true });
  });

  it('parses --bypass-row-limit', () => {
    expect(parseArgs(['--bypass-row-limit'])).toMatchObject({ bypassRowLimit: true });
  });

  it('parses --concurrency', () => {
    expect(parseArgs(['--concurrency', '5'])).toMatchObject({ concurrency: 5 });
  });

  it('ignores --concurrency with a non-positive value and preserves the remaining positional', () => {
    const r0 = parseArgs(['--concurrency', '0', 'input.csv']);
    expect(r0.concurrency).toBeUndefined();
    expect(r0.csvPath).toBe('input.csv');
    // -1 starts with '-' so the guard prevents it being consumed as a value
    expect(parseArgs(['--concurrency', '-1']).concurrency).toBeUndefined();
  });

  it('parses --max-retries including 0', () => {
    expect(parseArgs(['--max-retries', '0'])).toMatchObject({ maxRetries: 0 });
    expect(parseArgs(['--max-retries', '3'])).toMatchObject({ maxRetries: 3 });
  });

  it('parses API key flags (space form)', () => {
    expect(parseArgs(['--google-api-key', 'gkey'])).toMatchObject({ googleApiKey: 'gkey' });
    expect(parseArgs(['--openai-api-key', 'okey'])).toMatchObject({ openaiApiKey: 'okey' });
    expect(parseArgs(['--anthropic-api-key', 'akey'])).toMatchObject({ anthropicApiKey: 'akey' });
  });

  it('parses API key flags (= form)', () => {
    expect(parseArgs(['--google-api-key=gkey'])).toMatchObject({ googleApiKey: 'gkey' });
    expect(parseArgs(['--openai-api-key=okey'])).toMatchObject({ openaiApiKey: 'okey' });
    expect(parseArgs(['--anthropic-api-key=akey'])).toMatchObject({ anthropicApiKey: 'akey' });
  });

  it('parses --model-override in = form', () => {
    expect(parseArgs(['--model-override=anthropic:claude-opus-4-8'])).toMatchObject({
      modelOverride: 'anthropic:claude-opus-4-8',
    });
  });

  it('parses --output-dir in = form', () => {
    expect(parseArgs(['--output-dir=./out'])).toMatchObject({ outputDir: './out' });
  });

  it('parses --output-dir', () => {
    expect(parseArgs(['--output-dir', './out'])).toMatchObject({ outputDir: './out' });
  });

  it('captures an empty-string value from --output-dir= so the caller can validate it', () => {
    expect(parseArgs(['--output-dir='])).toMatchObject({ outputDir: '' });
  });

  it('parses --model-override', () => {
    expect(parseArgs(['--model-override', 'anthropic:claude-opus-4-8'])).toMatchObject({
      modelOverride: 'anthropic:claude-opus-4-8',
    });
  });

  it('ignores unknown boolean flags', () => {
    expect(parseArgs(['--unknown-flag'])).toEqual({});
  });

  it('treats the token after an unknown flag as positional csv (known limitation of flag-less parsers)', () => {
    // Without a schema we cannot tell whether '3' is a value for '--concurreny' or a positional.
    // We accept this: passing CSV as the first argument avoids the ambiguity entirely.
    const result = parseArgs(['--concurreny', '3', 'input.csv']);
    expect(result.csvPath).toBe('3');
    expect(result.concurrency).toBeUndefined();
  });

  it('does not consume another -- flag as the value of --concurrency', () => {
    const result = parseArgs(['--concurrency', '--no-telemetry']);
    expect(result.concurrency).toBeUndefined();
    expect(result.noTelemetry).toBe(true);
  });

  it('does not consume a single-dash flag (-h) as the value of --concurrency', () => {
    const result = parseArgs(['--concurrency', '-h']);
    expect(result.concurrency).toBeUndefined();
    expect(result.help).toBe(true);
  });

  it('does not swallow the positional csv when an unknown flag precedes it', () => {
    const result = parseArgs(['--unknown', 'input.csv']);
    expect(result.csvPath).toBe('input.csv');
  });

  it('silently ignores --concurrency when no value follows', () => {
    expect(parseArgs(['--concurrency']).concurrency).toBeUndefined();
  });

  it('silently ignores --concurrency with a non-integer value, still captures remaining args', () => {
    const result = parseArgs(['--concurrency', 'abc', 'input.csv']);
    expect(result.concurrency).toBeUndefined();
    expect(result.csvPath).toBe('input.csv');
  });

  it('handles a fully-specified invocation', () => {
    const result = parseArgs([
      'input.csv',
      '--model-override', 'anthropic:claude-opus-4-8',
      '--anthropic-api-key', 'akey',
      '--output-dir', './results',
      '--concurrency', '5',
      '--no-telemetry',
    ]);
    expect(result).toMatchObject({
      csvPath: 'input.csv',
      modelOverride: 'anthropic:claude-opus-4-8',
      anthropicApiKey: 'akey',
      outputDir: './results',
      concurrency: 5,
      noTelemetry: true,
    });
  });
});

// ---- requiredProviders ----

const makeGroup = (overrides: Partial<EvaluatorGroup> = {}): EvaluatorGroup => ({
  id: 'text-complexity',
  name: 'Text Complexity',
  description: '',
  evaluatorIds: [],
  requiresGoogleKey: true,
  requiresOpenAIKey: true,
  maxInputRows: 50,
  ...overrides,
});

describe('requiredProviders', () => {
  it('returns Google and OpenAI when the group requires both and no override is set', () => {
    const providers = requiredProviders(makeGroup(), undefined);
    expect(providers).toContain(Provider.Google);
    expect(providers).toContain(Provider.OpenAI);
    expect(providers).toHaveLength(2);
  });

  it('returns only the override provider when a model override is set', () => {
    const override = { provider: Provider.Anthropic, model: 'claude-opus-4-8' };
    expect(requiredProviders(makeGroup(), override)).toEqual([Provider.Anthropic]);
  });

  it('returns only Google when override targets Google', () => {
    const override = { provider: Provider.Google, model: 'gemini-2.5-pro' };
    expect(requiredProviders(makeGroup(), override)).toEqual([Provider.Google]);
  });

  it('returns only OpenAI when override targets OpenAI', () => {
    const override = { provider: Provider.OpenAI, model: 'gpt-4o' };
    expect(requiredProviders(makeGroup(), override)).toEqual([Provider.OpenAI]);
  });

  it('respects group that only requires one key', () => {
    const googleOnlyGroup = makeGroup({ requiresOpenAIKey: false });
    const providers = requiredProviders(googleOnlyGroup, undefined);
    expect(providers).toEqual([Provider.Google]);
  });

  it('returns empty array for a group requiring neither key', () => {
    const noKeyGroup = makeGroup({ requiresGoogleKey: false, requiresOpenAIKey: false });
    expect(requiredProviders(noKeyGroup, undefined)).toEqual([]);
  });
});
