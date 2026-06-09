import { Provider } from '../evaluators/base.js';
import type { ModelOverride } from '../evaluators/base.js';
import type { EvaluatorGroup } from './types.js';

export interface CliArgs {
  csv?: string;
  concurrency?: number;
  maxRetries?: number;
  noTelemetry?: boolean;
  bypassRowLimit?: boolean;
  googleApiKey?: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  outputDir?: string;
  model?: string;
  help?: boolean;
  version?: boolean;
}

export function parseArgs(argv: string[] = process.argv.slice(2)): CliArgs {
  const result: CliArgs = {};

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];

    if (arg === '--help' || arg === '-h') {
      result.help = true;
    } else if (arg === '--version') {
      result.version = true;
    } else if (arg === '--no-telemetry') {
      result.noTelemetry = true;
    } else if (arg === '--bypass-row-limit') {
      result.bypassRowLimit = true;
    } else if (arg === '--concurrency' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      const v = parseInt(argv[++i], 10);
      if (!isNaN(v) && v > 0) result.concurrency = v;
    } else if (arg === '--max-retries' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      const v = parseInt(argv[++i], 10);
      if (!isNaN(v) && v >= 0) result.maxRetries = v;
    } else if (arg === '--google-api-key' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.googleApiKey = argv[++i];
    } else if (arg === '--openai-api-key' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.openaiApiKey = argv[++i];
    } else if (arg === '--anthropic-api-key' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.anthropicApiKey = argv[++i];
    } else if (arg === '--output-dir' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.outputDir = argv[++i];
    } else if (arg === '--model' && argv[i + 1] && !argv[i + 1].startsWith('-')) {
      result.model = argv[++i];
    } else if (!arg.startsWith('-') && !result.csv) {
      result.csv = arg;
    }
  }

  return result;
}

export function parseModelOverride(raw: string): ModelOverride {
  const colonIdx = raw.indexOf(':');
  if (colonIdx === -1) {
    throw new Error(
      `--model requires "provider:model" format (e.g. anthropic:claude-opus-4-8), got: "${raw}"`
    );
  }
  const providerStr = raw.slice(0, colonIdx).toLowerCase();
  const model = raw.slice(colonIdx + 1).trim();

  const validProviders = Object.values(Provider);
  if (!validProviders.includes(providerStr as Provider)) {
    throw new Error(
      `Unknown provider "${providerStr}" in --model. Valid providers: ${validProviders.join(', ')}`
    );
  }
  if (!model) {
    throw new Error(`Model name cannot be empty. Use: --model ${providerStr}:<model-id>`);
  }

  return { provider: providerStr as Provider, model };
}

export function requiredProviders(
  group: EvaluatorGroup,
  modelOverride: ModelOverride | undefined
): Provider[] {
  if (modelOverride) return [modelOverride.provider];
  const providers: Provider[] = [];
  if (group.requiresGoogleKey) providers.push(Provider.Google);
  if (group.requiresOpenAIKey) providers.push(Provider.OpenAI);
  return providers;
}
