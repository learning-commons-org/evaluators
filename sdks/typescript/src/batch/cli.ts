import * as fs from 'fs';
import * as path from 'path';
import { randomUUID } from 'crypto';
import prompts from 'prompts';
import {
  BatchEvaluator,
  getFamilies,
  getFamily,
  parseCSV,
  renderOutputs,
  Provider,
  type BatchInput,
  type ModelOverride,
  type ReportMeta,
  type EvaluatorFamily,
} from './index.js';
import type { KeyKind } from './families/family.js';
import { resolveMembers } from './families/family.js';
import { ProgressTracker } from './progress.js';
import { getSDKVersion } from '../telemetry/index.js';
import { parseArgs, resolveModel, MODEL_SHORTCODES } from './cli-args.js';

// ---- Output directory validation ----

function validateOutputDir(value: string): string | true {
  const trimmed = value.trim();
  if (!trimmed) return 'Output directory cannot be empty';
  const resolved = path.resolve(trimmed);

  if (fs.existsSync(resolved)) {
    try {
      if (!fs.statSync(resolved).isDirectory()) return `Path exists but is not a directory: ${resolved}`;
    } catch {
      return `Cannot access path: ${resolved}`;
    }
  }

  const checkDir = fs.existsSync(resolved) ? resolved : path.dirname(resolved);
  if (!fs.existsSync(checkDir)) {
    return `Parent directory does not exist: ${path.dirname(resolved)}`;
  }
  try {
    const testFile = path.join(checkDir, `.write-test-${randomUUID()}`);
    fs.writeFileSync(testFile, '');
    fs.unlinkSync(testFile);
    return true;
  } catch (error) {
    const code = (error as { code?: string }).code;
    if (code === 'EACCES') return `No write permission for directory: ${checkDir}`;
    if (code === 'EROFS') return `Directory is read-only: ${checkDir}`;
    return `Cannot write to directory: ${error instanceof Error ? error.message : String(error)}`;
  }
}

// ---- Credentials ----

const KEY_CONFIG: Record<KeyKind, { envVar: string; label: string; flag: string }> = {
  [Provider.Google]: { envVar: 'GOOGLE_API_KEY', label: 'Google API Key', flag: '--google-api-key' },
  [Provider.OpenAI]: { envVar: 'OPENAI_API_KEY', label: 'OpenAI API Key', flag: '--openai-api-key' },
  [Provider.Anthropic]: { envVar: 'ANTHROPIC_API_KEY', label: 'Anthropic API Key', flag: '--anthropic-api-key' },
  'learning-commons': { envVar: 'LEARNING_COMMONS_API_KEY', label: 'Learning Commons API Key', flag: '--learning-commons-api-key' },
};

// ---- Help / version ----

function printHelp(): void {
  const families = getFamilies()
    .map((f) => `    ${f.id}  (${f.members.map((m) => m.id).join(', ')})`)
    .join('\n');
  console.log(`evaluators-batch v${getSDKVersion()}

Usage: evaluators-batch [input.csv] [options]

  input.csv              Path to the CSV file (columns depend on the family)

Family & members:
  --family <id>              Evaluator family to run. Available:
${families}
  --evaluator <id[,id...]>   Run only these members (repeatable). Default: all.

Model:
  --model <alias|provider:model>  Override the model for all members.
                                  Shortcodes: ${Object.keys(MODEL_SHORTCODES).join(', ')}
                                  Or "provider:model" (e.g. anthropic:claude-opus-4-8).

API Keys (flag > env var; prompted when interactive, required otherwise):
  --google-api-key <key>     (env: GOOGLE_API_KEY)
  --openai-api-key <key>     (env: OPENAI_API_KEY)
  --anthropic-api-key <key>  (env: ANTHROPIC_API_KEY)
  --learning-commons-api-key <key> (env: LEARNING_COMMONS_API_KEY) — required by math-standards-alignment

Output:
  --output-dir <path>        Write results here (default: ./batch-results-<timestamp>)
                             Produces results.csv, results.json, results.html

Evaluation:
  --concurrency <n>          Max parallel evaluations (default: 3)
  --max-retries <n>          Retries per failed call (default: 2)
  --bypass-row-limit         Skip the per-family row limit check
  --no-telemetry             Disable usage telemetry

  -y, --yes                  Non-interactive: never prompt, error on missing input
  --version                  Print version and exit
  --help                     Show this help`);
}

// ---- Interactive helpers ----

async function resolveKey(
  kind: KeyKind,
  fromFlag: string | undefined,
  interactive: boolean,
): Promise<string> {
  const { envVar, label, flag } = KEY_CONFIG[kind];
  if (fromFlag !== undefined) {
    if (!fromFlag) {
      console.error(`❌ ${label} (${flag}) was provided but is empty`);
      process.exit(1);
    }
    return fromFlag;
  }
  const fromEnv = process.env[envVar];
  if (fromEnv) return fromEnv;

  if (!interactive) {
    console.error(`❌ Missing ${label}. Provide ${flag} or set ${envVar} (running non-interactively).`);
    process.exit(1);
  }

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

async function selectFamily(cliFamily: string | undefined, interactive: boolean): Promise<EvaluatorFamily> {
  if (cliFamily) return getFamily(cliFamily);
  const families = getFamilies();
  if (!interactive) {
    console.error(`❌ Specify --family. Available: ${families.map((f) => f.id).join(', ')}`);
    process.exit(1);
  }
  const { familyId } = await prompts({
    type: 'select',
    name: 'familyId',
    message: 'Which evaluator family?',
    choices: families.map((f) => ({ title: `${f.name} — ${f.description}`, value: f.id })),
  });
  if (!familyId) {
    console.log('Cancelled.');
    process.exit(0);
  }
  return getFamily(familyId as string);
}

async function selectMembers(
  family: EvaluatorFamily,
  cliEvaluators: string[] | undefined,
  interactive: boolean,
): Promise<string[] | undefined> {
  if (cliEvaluators && cliEvaluators.length > 0) {
    resolveMembers(family, cliEvaluators); // validates ids, throws on unknown
    return cliEvaluators;
  }
  if (!interactive || family.members.length <= 1) return undefined; // all members
  const { selected } = await prompts({
    type: 'multiselect',
    name: 'selected',
    message: 'Which evaluators? (space to toggle, enter to confirm)',
    choices: family.members.map((m) => ({ title: m.name, value: m.id, selected: true })),
    instructions: false,
    hint: '- all selected by default',
  });
  if (!selected || (selected as string[]).length === 0) return undefined; // treat none as all
  return selected as string[];
}

async function selectModel(
  cliArgs: ReturnType<typeof parseArgs>,
  interactive: boolean,
): Promise<ModelOverride | undefined> {
  const raw = cliArgs.model ?? cliArgs.modelOverride;
  if (raw !== undefined) return resolveModel(raw);
  if (!interactive) return undefined;

  const { useDefault } = await prompts({
    type: 'confirm',
    name: 'useDefault',
    message: 'Use each evaluator’s default model?',
    initial: true,
  });
  if (useDefault !== false) return undefined;

  const { model } = await prompts({
    type: 'text',
    name: 'model',
    message: `Model (shortcode [${Object.keys(MODEL_SHORTCODES).join(', ')}] or provider:model):`,
    validate: (value) => {
      try { resolveModel(value); return true; } catch (e) { return e instanceof Error ? e.message : 'Invalid model'; }
    },
  });
  if (!model) return undefined;
  return resolveModel(model as string);
}

// ---- Main ----

async function main() {
  const cliArgs = parseArgs();

  if (cliArgs.help) { printHelp(); process.exit(0); }
  if (cliArgs.version) { console.log(getSDKVersion()); process.exit(0); }

  // Non-interactive when --yes is passed or either stream lacks a terminal
  // (CI, or stdout redirected to a file). Prompting needs a real stdin+stdout.
  const interactive = !cliArgs.yes && Boolean(process.stdin.isTTY && process.stdout.isTTY);

  console.log('\n📊 Batch CSV Evaluator\n');

  try {
    // 1. Family + members
    const family = await selectFamily(cliArgs.family, interactive);
    const selectedMemberIds = await selectMembers(family, cliArgs.evaluators, interactive);
    const members = resolveMembers(family, selectedMemberIds);

    // 2. Model choice (before keys, so key requirements reflect any override)
    const modelOverride = await selectModel(cliArgs, interactive);

    // 3. CSV
    let inputs: BatchInput[] = [];
    let csvPath: string;
    if (cliArgs.csvPath !== undefined) {
      csvPath = cliArgs.csvPath;
      try {
        inputs = parseCSV(csvPath);
      } catch (error) {
        console.error(`❌ ${error instanceof Error ? error.message : 'Invalid CSV file'}`);
        process.exit(1);
      }
    } else if (interactive) {
      const response = await prompts({
        type: 'text',
        name: 'csvPath',
        message: 'Where is your CSV file?',
        initial: './input.csv',
        validate: (value) => {
          try { inputs = parseCSV(value); return true; } catch (e) { return e instanceof Error ? e.message : 'Invalid CSV file'; }
        },
      });
      if (!response.csvPath) { console.log('No file path provided.'); process.exit(0); }
      csvPath = response.csvPath as string;
    } else {
      console.error('❌ No CSV provided. Pass the CSV path as the first argument.');
      process.exit(1);
    }

    console.log(`\n✓ ${inputs.length} rows · family: ${family.name} · evaluators: ${members.map((m) => m.id).join(', ')}`);
    if (modelOverride) console.log(`  ⚡ Model override: ${modelOverride.provider}:${modelOverride.model}`);

    // 4. Row limit (fail fast before prompting for keys)
    if (inputs.length > family.maxInputRows && !cliArgs.bypassRowLimit) {
      console.error(`\n❌ Too many rows: ${inputs.length} (max ${family.maxInputRows} for "${family.id}").`);
      console.error('   Trim the CSV, split into batches, or re-run with --bypass-row-limit.');
      process.exit(1);
    }

    // 5. Keys — exactly what this family + selection + override requires
    const requiredKeys = family.requiredKeys(members.map((m) => m.id), modelOverride);
    const flagFor: Record<KeyKind, string | undefined> = {
      [Provider.Google]: cliArgs.googleApiKey,
      [Provider.OpenAI]: cliArgs.openaiApiKey,
      [Provider.Anthropic]: cliArgs.anthropicApiKey,
      'learning-commons': cliArgs.learningCommonsApiKey,
    };
    const keys: Partial<Record<KeyKind, string>> = {};
    for (const kind of requiredKeys) {
      keys[kind] = await resolveKey(kind, flagFor[kind], interactive);
    }

    // 6. Output dir
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    const defaultOutputDir = path.join(process.cwd(), `batch-results-${timestamp}`);
    let outputDir: string;
    if (cliArgs.outputDir !== undefined) {
      const validation = validateOutputDir(cliArgs.outputDir);
      if (validation !== true) { console.error(`❌ Invalid --output-dir: ${validation}`); process.exit(1); }
      outputDir = path.resolve(cliArgs.outputDir.trim());
    } else if (interactive) {
      const response = await prompts({
        type: 'text', name: 'outputDir', message: 'Output directory:', initial: defaultOutputDir, validate: validateOutputDir,
      });
      if (!response.outputDir) { console.log('No output directory provided.'); process.exit(0); }
      outputDir = path.resolve((response.outputDir as string).trim());
    } else {
      outputDir = defaultOutputDir;
    }
    fs.mkdirSync(outputDir, { recursive: true });

    const csvBasename = path.basename(csvPath, path.extname(csvPath));
    const reportMeta: ReportMeta = {
      csvPath: path.resolve(csvPath),
      groupId: family.id,
      reportId: `${csvBasename.replace(/[^a-zA-Z0-9]/g, '_')}_${timestamp}`,
      generatedAt: now,
      totalInputRows: inputs.length,
    };

    // 7. Confirm (interactive only)
    const totalTasks = inputs.length * members.length;
    console.log(`\n📝 ${totalTasks} tasks · concurrency ${cliArgs.concurrency ?? 3} · output ${outputDir}\n`);
    if (interactive) {
      const { confirm } = await prompts({ type: 'confirm', name: 'confirm', message: 'Start batch evaluation?', initial: true });
      if (!confirm) { console.log('Cancelled.'); process.exit(0); }
    }

    // 8. Run
    console.log('='.repeat(60));
    const tracker = new ProgressTracker(totalTasks);
    const evaluationStartTime = Date.now();
    const evaluator = new BatchEvaluator({
      googleApiKey: keys[Provider.Google],
      openaiApiKey: keys[Provider.OpenAI],
      anthropicApiKey: keys[Provider.Anthropic],
      learningCommonsApiKey: keys['learning-commons'],
      concurrency: cliArgs.concurrency ?? 3,
      maxRetries: cliArgs.maxRetries ?? 2,
      telemetry: !cliArgs.noTelemetry,
      bypassRowLimit: cliArgs.bypassRowLimit ?? false,
      modelOverride,
    });

    let isShuttingDown = false;
    const handleShutdown = () => {
      if (isShuttingDown) { console.log('\n\n⚠️  Force quit.'); process.exit(1); }
      isShuttingDown = true;
      console.log('\n\n⚠️  Shutdown requested. Saving partial results…\n');
      const partial = evaluator.cancel();
      if (partial.length > 0) {
        try {
          const bundle = renderOutputs(family.id, { results: partial, summary: {
            totalTasks: partial.length,
            successful: partial.filter((r) => r.status === 'success').length,
            failed: partial.filter((r) => r.status === 'error').length,
            durationMs: Date.now() - evaluationStartTime,
            resultsPerEvaluator: {},
          } }, reportMeta);
          fs.writeFileSync(path.join(outputDir, 'results-partial.csv'), bundle.csv);
          fs.writeFileSync(path.join(outputDir, 'results-partial.json'), bundle.json);
          fs.writeFileSync(path.join(outputDir, 'results-partial.html'), bundle.html);
          console.log(`✓ Saved ${partial.length} partial results to ${outputDir}/\n`);
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
      output = await evaluator.evaluate(inputs, family.id, {
        selectedMemberIds,
        onProgress: (result) => { tracker.update(result); tracker.display(); },
      });
    } finally {
      process.off('SIGINT', handleShutdown);
      process.off('SIGTERM', handleShutdown);
    }

    tracker.displaySummary();

    // 9. Write outputs
    try {
      const bundle = renderOutputs(family.id, output, reportMeta);
      fs.writeFileSync(path.join(outputDir, 'results.csv'), bundle.csv);
      fs.writeFileSync(path.join(outputDir, 'results.json'), bundle.json);
      fs.writeFileSync(path.join(outputDir, 'results.html'), bundle.html);
      console.log('\n📄 Output files:');
      console.log(`  ${outputDir}/`);
      console.log('    ├── results.csv');
      console.log('    ├── results.json');
      console.log('    └── results.html');
      console.log(`\nOpen the report: ${path.join(outputDir, 'results.html')}`);
    } catch (error) {
      console.error('\n❌ Error writing output files:');
      if (error instanceof Error) console.error(`  ${error.message}`);
      process.exit(1);
    }
  } catch (error) {
    console.error('\n❌ Error:', error instanceof Error ? error.message : String(error));
    process.exit(1);
  }
}

main();
