import { Provider } from '../evaluators/base.js';
import type { ModelOverride } from '../evaluators/base.js';
import type { EvaluatorGroup } from './types.js';

export interface CliArgs {
  csvPath?: string;
  concurrency?: number;
  maxRetries?: number;
  noTelemetry?: boolean;
  bypassRowLimit?: boolean;
  googleApiKey?: string;
  openaiApiKey?: string;
  anthropicApiKey?: string;
  outputDir?: string;
  modelOverride?: string;
  help?: boolean;
  version?: boolean;
}

export function parseArgs(argv: string[] = process.argv.slice(2)): CliArgs {
  // Normalise --flag=value into ['--flag', 'value'] so the loop handles both forms identically
  const args: string[] = [];
  for (const a of argv) {
    const eqIdx = a.startsWith('--') ? a.indexOf('=') : -1;
    if (eqIdx !== -1) {
      args.push(a.slice(0, eqIdx), a.slice(eqIdx + 1));
    } else {
      args.push(a);
    }
  }

  const result: CliArgs = {};

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    if (arg === '--help' || arg === '-h') {
      result.help = true;
    } else if (arg === '--version') {
      result.version = true;
    } else if (arg === '--no-telemetry') {
      result.noTelemetry = true;
    } else if (arg === '--bypass-row-limit') {
      result.bypassRowLimit = true;
    } else if (arg === '--concurrency' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      const v = parseInt(args[++i], 10);
      if (!isNaN(v) && v > 0) result.concurrency = v;
    } else if (arg === '--max-retries' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      const v = parseInt(args[++i], 10);
      if (!isNaN(v) && v >= 0) result.maxRetries = v;
    } else if (arg === '--google-api-key' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      result.googleApiKey = args[++i];
    } else if (arg === '--openai-api-key' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      result.openaiApiKey = args[++i];
    } else if (arg === '--anthropic-api-key' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      result.anthropicApiKey = args[++i];
    } else if (arg === '--output-dir' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      result.outputDir = args[++i];
    } else if (arg === '--model-override' && i + 1 < args.length && !args[i + 1].startsWith('-')) {
      result.modelOverride = args[++i];
    } else if (!arg.startsWith('-') && result.csvPath === undefined) {
      result.csvPath = arg;
    }
  }

  return result;
}


export function parseModelOverride(raw: string): ModelOverride {
  const colonIdx = raw.indexOf(':');
  if (colonIdx === -1) {
    throw new Error(
      `--model-override requires "provider:model" format (e.g. anthropic:claude-opus-4-8), got: "${raw}"`
    );
  }
  const providerStr = raw.slice(0, colonIdx).toLowerCase().trim();
  const model = raw.slice(colonIdx + 1).trim();

  const validProviders = Object.values(Provider);
  if (!validProviders.includes(providerStr as Provider)) {
    throw new Error(
      `Unknown provider "${providerStr}" in --model-override. Valid providers: ${validProviders.join(', ')}`
    );
  }
  if (!model) {
    throw new Error(`Model name cannot be empty. Use: --model-override ${providerStr}:<model-id>`);
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
