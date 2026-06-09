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
});

// ---- parseArgs ----

describe('parseArgs', () => {
  it('returns empty object for no args', () => {
    expect(parseArgs([])).toEqual({});
  });

  it('captures the first non-flag argument as csv', () => {
    expect(parseArgs(['input.csv'])).toMatchObject({ csv: 'input.csv' });
  });

  it('ignores a second positional argument', () => {
    expect(parseArgs(['a.csv', 'b.csv'])).toMatchObject({ csv: 'a.csv' });
  });

  it('does not treat a value arg as the csv path', () => {
    // '3' is the value of --concurrency, not a positional csv
    const result = parseArgs(['--concurrency', '3', 'input.csv']);
    expect(result.csv).toBe('input.csv');
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

  it('ignores --concurrency with a non-positive value', () => {
    expect(parseArgs(['--concurrency', '0']).concurrency).toBeUndefined();
    expect(parseArgs(['--concurrency', '-1']).concurrency).toBeUndefined();
  });

  it('parses --max-retries including 0', () => {
    expect(parseArgs(['--max-retries', '0'])).toMatchObject({ maxRetries: 0 });
    expect(parseArgs(['--max-retries', '3'])).toMatchObject({ maxRetries: 3 });
  });

  it('parses API key flags', () => {
    expect(parseArgs(['--google-api-key', 'gkey'])).toMatchObject({ googleApiKey: 'gkey' });
    expect(parseArgs(['--openai-api-key', 'okey'])).toMatchObject({ openaiApiKey: 'okey' });
    expect(parseArgs(['--anthropic-api-key', 'akey'])).toMatchObject({ anthropicApiKey: 'akey' });
  });

  it('parses --output-dir', () => {
    expect(parseArgs(['--output-dir', './out'])).toMatchObject({ outputDir: './out' });
  });

  it('parses --model', () => {
    expect(parseArgs(['--model', 'anthropic:claude-opus-4-8'])).toMatchObject({
      model: 'anthropic:claude-opus-4-8',
    });
  });

  it('ignores unknown flags', () => {
    expect(parseArgs(['--unknown-flag'])).toEqual({});
  });

  it('handles a fully-specified invocation', () => {
    const result = parseArgs([
      'input.csv',
      '--model', 'anthropic:claude-opus-4-8',
      '--anthropic-api-key', 'akey',
      '--output-dir', './results',
      '--concurrency', '5',
      '--no-telemetry',
    ]);
    expect(result).toMatchObject({
      csv: 'input.csv',
      model: 'anthropic:claude-opus-4-8',
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
});
