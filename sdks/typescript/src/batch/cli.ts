import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import prompts from 'prompts';
import {
  BatchEvaluator,
  getAvailableGroups,
  parseCSV,
  formatAsCSV,
  formatAsHTML,
  Provider,
  type BatchInput,
  type ModelOverride,
  type ReportMeta,
} from './index.js';
import { ProgressTracker } from './progress.js';
import { getSDKVersion } from '../telemetry/index.js';

// ---- Types ----

interface CliArgs {
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

// ---- Argument parsing ----

function parseArgs(): CliArgs {
  const rawArgs = process.argv.slice(2);
  const result: CliArgs = {};

  for (let i = 0; i < rawArgs.length; i++) {
    const arg = rawArgs[i];

    if (arg === '--help' || arg === '-h') {
      result.help = true;
    } else if (arg === '--version') {
      result.version = true;
    } else if (arg === '--no-telemetry') {
      result.noTelemetry = true;
    } else if (arg === '--bypass-row-limit') {
      result.bypassRowLimit = true;
    } else if (arg === '--concurrency' && rawArgs[i + 1]) {
      const v = parseInt(rawArgs[++i], 10);
      if (!isNaN(v) && v > 0) result.concurrency = v;
    } else if (arg === '--max-retries' && rawArgs[i + 1]) {
      const v = parseInt(rawArgs[++i], 10);
      if (!isNaN(v) && v >= 0) result.maxRetries = v;
    } else if (arg === '--google-api-key' && rawArgs[i + 1]) {
      result.googleApiKey = rawArgs[++i];
    } else if (arg === '--openai-api-key' && rawArgs[i + 1]) {
      result.openaiApiKey = rawArgs[++i];
    } else if (arg === '--anthropic-api-key' && rawArgs[i + 1]) {
      result.anthropicApiKey = rawArgs[++i];
    } else if (arg === '--output-dir' && rawArgs[i + 1]) {
      result.outputDir = rawArgs[++i];
    } else if (arg === '--model' && rawArgs[i + 1]) {
      result.model = rawArgs[++i];
    } else if (!arg.startsWith('--') && !result.csv) {
      result.csv = arg;
    }
  }

  return result;
}

function parseModelOverride(raw: string): ModelOverride {
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

// ---- Help / version ----

function printHelp(): void {
  console.log(`evaluators-batch v${getSDKVersion()}\n`);
  console.log(`Usage: evaluators-batch [input.csv] [options]\n`);
  console.log(`  input.csv              Path to the CSV file (requires "text" and "grade" columns)\n`);
  console.log(`API Keys (flag takes priority over env var; if neither is set, you will be prompted):`);
  console.log(`  --google-api-key <key>     Google API key    (env: GOOGLE_API_KEY)`);
  console.log(`  --openai-api-key <key>     OpenAI API key    (env: OPENAI_API_KEY)`);
  console.log(`  --anthropic-api-key <key>  Anthropic API key (env: ANTHROPIC_API_KEY)\n`);
  console.log(`Model Override:`);
  console.log(`  --model <provider:model>   Use a specific model for all evaluators`);
  console.log(`                             Providers: openai, google, anthropic`);
  console.log(`                             Example: --model anthropic:claude-opus-4-8`);
  console.log(`                             When set, only that provider's key is required.\n`);
  console.log(`Output:`);
  console.log(`  --output-dir <path>        Write results here (default: ./batch-results-<timestamp>)\n`);
  console.log(`Evaluation:`);
  console.log(`  --concurrency <n>          Max parallel evaluations (default: 3)`);
  console.log(`  --max-retries <n>          Retries per failed call (default: 2)`);
  console.log(`  --bypass-row-limit         Skip the per-group row limit check`);
  console.log(`  --no-telemetry             Disable usage telemetry\n`);
  console.log(`  --version                  Print version and exit`);
  console.log(`  --help                     Show this help`);
}

// ---- API key resolution ----

const KEY_CONFIG: Record<Provider, { envVar: string; label: string }> = {
  [Provider.Google]:    { envVar: 'GOOGLE_API_KEY',    label: 'Google API Key'    },
  [Provider.OpenAI]:   { envVar: 'OPENAI_API_KEY',    label: 'OpenAI API Key'    },
  [Provider.Anthropic]:{ envVar: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key' },
};

async function resolveApiKey(provider: Provider, fromFlag: string | undefined): Promise<string> {
  const { envVar, label } = KEY_CONFIG[provider];
  const fromEnv = process.env[envVar];

  if (fromFlag) return fromFlag;
  if (fromEnv) return fromEnv;

  const result = await prompts({
    type: 'password',
    name: 'key',
    message: `${label}:`,
    validate: (value) => (value ? true : `${label} is required`),
  });

  if (!result.key) {
    console.log('Cancelled.');
    process.exit(0);
  }

  return result.key as string;
}

function requiredProviders(
  group: ReturnType<typeof getAvailableGroups>[number],
  modelOverride: ModelOverride | undefined
): Provider[] {
  if (modelOverride) return [modelOverride.provider];
  const providers: Provider[] = [];
  if (group.requiresGoogleKey) providers.push(Provider.Google);
  if (group.requiresOpenAIKey) providers.push(Provider.OpenAI);
  return providers;
}

// ---- Main ----

async function main() {
  const cliArgs = parseArgs();

  if (cliArgs.help) {
    printHelp();
    process.exit(0);
  }

  if (cliArgs.version) {
    console.log(getSDKVersion());
    process.exit(0);
  }

  // Parse model override early so errors surface before any prompts
  let modelOverride: ModelOverride | undefined;
  if (cliArgs.model) {
    try {
      modelOverride = parseModelOverride(cliArgs.model);
    } catch (error) {
      console.error(`❌ ${error instanceof Error ? error.message : String(error)}`);
      process.exit(1);
    }
  }

  console.log('\n📊 Batch CSV Evaluator\n');
  console.log('This tool will evaluate multiple texts using one or more evaluators.\n');

  try {
    // Step 1: CSV path — use positional arg or prompt
    let inputs: BatchInput[] = [];
    let csvPath: string;

    if (cliArgs.csv) {
      try {
        inputs = parseCSV(cliArgs.csv);
        csvPath = cliArgs.csv;
      } catch (error) {
        console.error(`❌ ${error instanceof Error ? error.message : 'Invalid CSV file'}`);
        process.exit(1);
      }
    } else {
      const response = await prompts({
        type: 'text',
        name: 'csvPath',
        message: 'Where is your CSV file?',
        initial: './input.csv',
        validate: (value) => {
          try {
            inputs = parseCSV(value);
            return true;
          } catch (error) {
            return error instanceof Error ? error.message : 'Invalid CSV file';
          }
        },
      });

      if (!response.csvPath) {
        console.log('No file path provided. Run the command again to start over.');
        process.exit(0);
      }

      csvPath = response.csvPath as string;
    }

    console.log(`\n✓ Found ${inputs.length} rows in CSV\n`);

    // Step 2: Show the evaluator group that will run
    const group = getAvailableGroups()[0];
    console.log(`✓ Evaluator group: ${group.name}`);
    console.log(`  ${group.description}`);
    if (modelOverride) {
      console.log(`  ⚡ Model override: ${modelOverride.provider}:${modelOverride.model}`);
    }
    console.log();

    // Enforce row limit before prompting for API keys
    if (inputs.length > group.maxInputRows) {
      if (cliArgs.bypassRowLimit) {
        console.warn(`⚠️  Row limit bypassed: ${inputs.length} rows (default max ${group.maxInputRows}).`);
        console.warn(`   Expect longer runtime and possible provider throttling.\n`);
      } else {
        console.error(`❌ Too many rows: ${inputs.length} (max ${group.maxInputRows} for this group)\n`);
        console.log('Options:');
        console.log(`  • Trim the CSV to ${group.maxInputRows} rows`);
        console.log('  • Split into multiple smaller batches');
        console.log(`  • Re-run with --bypass-row-limit to skip this check:\n`);
        console.log(`    evaluators-batch ${process.argv.slice(2).filter(a => a !== '--bypass-row-limit').join(' ')} --bypass-row-limit\n`);
        process.exit(1);
      }
    }

    // Step 3: Resolve API keys — skip prompts for any key already provided
    const needed = requiredProviders(group, modelOverride);
    const keyFlagMap: Record<Provider, string | undefined> = {
      [Provider.Google]:    cliArgs.googleApiKey,
      [Provider.OpenAI]:   cliArgs.openaiApiKey,
      [Provider.Anthropic]:cliArgs.anthropicApiKey,
    };

    const resolvedKeys: Partial<Record<Provider, string>> = {};
    for (const provider of needed) {
      resolvedKeys[provider] = await resolveApiKey(provider, keyFlagMap[provider]);
    }

    // Step 4: Output directory — use flag or prompt
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    const defaultOutputDir = path.join(process.cwd(), `batch-results-${timestamp}`);

    let outputDir: string;

    if (cliArgs.outputDir) {
      outputDir = cliArgs.outputDir;
    } else {
      const response = await prompts({
        type: 'text',
        name: 'outputDir',
        message: 'Output directory:',
        initial: defaultOutputDir,
        validate: (value) => {
          const parentDir = path.dirname(value);
          if (!fs.existsSync(parentDir)) {
            return `Parent directory does not exist: ${parentDir}`;
          }
          try {
            const testFile = path.join(parentDir, '.write-test');
            fs.writeFileSync(testFile, '');
            fs.unlinkSync(testFile);
            return true;
          } catch (error) {
            if (error instanceof Error) {
              if (error.message.includes('EACCES')) return `No write permission for directory: ${parentDir}`;
              if (error.message.includes('EROFS')) return `Directory is read-only: ${parentDir}`;
              return `Cannot write to directory: ${error.message}`;
            }
            return 'Cannot write to directory';
          }
        },
      });

      if (!response.outputDir) {
        console.log('No output directory provided. Run the command again to start over.');
        process.exit(0);
      }

      outputDir = response.outputDir as string;
    }

    fs.mkdirSync(outputDir, { recursive: true });

    // Build report metadata
    const csvBasename = path.basename(csvPath, path.extname(csvPath));
    const reportMeta: ReportMeta = {
      csvPath: path.resolve(csvPath),
      groupId: group.id,
      reportId: `${csvBasename.replace(/[^a-zA-Z0-9]/g, '_')}_${timestamp}`,
      generatedAt: now,
      totalInputRows: inputs.length,
    };

    // Step 5: Confirm and run
    const totalTasks = inputs.length * group.evaluatorIds.length;

    console.log(`\n📝 Summary:`);
    console.log(`  Input rows:  ${inputs.length}${cliArgs.bypassRowLimit ? ' (row limit bypassed)' : ''}`);
    console.log(`  Evaluators:  ${group.evaluatorIds.length}`);
    console.log(`  Total tasks: ${totalTasks}`);
    console.log(`  Concurrency: ${cliArgs.concurrency ?? 3}`);
    console.log(`  Max retries: ${cliArgs.maxRetries ?? 2}`);
    if (modelOverride) {
      console.log(`  Model:       ${modelOverride.provider}:${modelOverride.model}`);
    }
    console.log(`  Output:      ${outputDir}\n`);

    const { confirm } = await prompts({
      type: 'confirm',
      name: 'confirm',
      message: 'Start batch evaluation?',
      initial: true,
    });

    if (!confirm) {
      console.log('Cancelled.');
      process.exit(0);
    }

    // Step 6: Run batch evaluation
    console.log('\n' + '='.repeat(60));
    const tracker = new ProgressTracker(totalTasks);
    const evaluationStartTime = Date.now();

    const evaluator = new BatchEvaluator({
      googleApiKey:    resolvedKeys[Provider.Google],
      openaiApiKey:    resolvedKeys[Provider.OpenAI],
      anthropicApiKey: resolvedKeys[Provider.Anthropic],
      concurrency:     cliArgs.concurrency ?? 3,
      maxRetries:      cliArgs.maxRetries ?? 2,
      telemetry:       !cliArgs.noTelemetry,
      bypassRowLimit:  cliArgs.bypassRowLimit ?? false,
      modelOverride,
    });

    // Handle Ctrl+C gracefully
    let isShuttingDown = false;
    const handleShutdown = () => {
      if (isShuttingDown) {
        console.log('\n\n⚠️  Force quit detected. Exiting immediately...');
        process.exit(1);
      }

      isShuttingDown = true;
      console.log('\n\n⚠️  Shutdown requested. Saving partial results...');
      console.log('   (Press Ctrl+C again to force quit)\n');

      const partialResults = evaluator.cancel();

      if (partialResults.length > 0) {
        const durationMs = Date.now() - evaluationStartTime;
        const partialOutput = {
          results: partialResults,
          summary: {
            totalTasks: partialResults.length,
            successful: partialResults.filter((r) => r.status === 'success').length,
            failed: partialResults.filter((r) => r.status === 'error').length,
            durationMs,
            resultsPerEvaluator: {},
          },
        };

        try {
          fs.writeFileSync(path.join(outputDir, 'results-partial.csv'), formatAsCSV(partialOutput));
          fs.writeFileSync(path.join(outputDir, 'results-partial.html'), formatAsHTML(partialOutput, reportMeta));

          console.log(`✓ Saved ${partialResults.length} results to:`);
          console.log(`  ${outputDir}/`);
          console.log(`    ├── results-partial.csv`);
          console.log(`    └── results-partial.html`);
          console.log();
        } catch (error) {
          console.error('❌ Error saving partial results:', error instanceof Error ? error.message : String(error));
        }
      } else {
        console.log('No results to save yet.\n');
      }

      process.exit(0);
    };

    process.on('SIGINT', handleShutdown);
    process.on('SIGTERM', handleShutdown);

    let output;
    try {
      output = await evaluator.evaluate(inputs, group.id, (result) => {
        tracker.update(result);
        tracker.display();
      });
    } finally {
      process.off('SIGINT', handleShutdown);
      process.off('SIGTERM', handleShutdown);
    }

    tracker.displaySummary();

    // Step 7: Write output files
    try {
      fs.writeFileSync(path.join(outputDir, 'results.csv'), formatAsCSV(output));
      fs.writeFileSync(path.join(outputDir, 'results.html'), formatAsHTML(output, reportMeta));

      console.log('📄 Output files generated:');
      console.log(`  ${outputDir}/`);
      console.log(`    ├── results.csv`);
      console.log(`    └── results.html`);
      console.log();

      const htmlPath = path.join(outputDir, 'results.html');
      const cmd = process.platform === 'win32' ? `start "" "${htmlPath}"` : `open "${htmlPath}"`;
      exec(cmd);
    } catch (error) {
      console.error('\n❌ Error writing output files:');
      if (error instanceof Error) console.error(`  ${error.message}`);
      console.error('\n⚠️  Evaluation completed but outputs could not be saved.');
      process.exit(1);
    }
  } catch (error) {
    console.error('\n❌ Error:', error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

main();
