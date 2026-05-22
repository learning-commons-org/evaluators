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
  type BatchInput,
  type ReportMeta,
} from './index.js';
import { ProgressTracker } from './progress.js';

interface CliArgs {
  concurrency?: number;
  maxRetries?: number;
  noTelemetry?: boolean;
  bypassRowLimit?: boolean;
}

function parseArgs(): CliArgs {
  const args = process.argv.slice(2);
  const result: CliArgs = {};

  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--concurrency' && args[i + 1]) {
      const v = parseInt(args[++i], 10);
      if (!isNaN(v) && v > 0) result.concurrency = v;
    } else if (args[i] === '--max-retries' && args[i + 1]) {
      const v = parseInt(args[++i], 10);
      if (!isNaN(v) && v >= 0) result.maxRetries = v;
    } else if (args[i] === '--no-telemetry') {
      result.noTelemetry = true;
    } else if (args[i] === '--bypass-row-limit') {
      result.bypassRowLimit = true;
    }
  }

  return result;
}

async function main() {
  const cliArgs = parseArgs();

  console.log('\n📊 Batch CSV Evaluator\n');
  console.log('This tool will evaluate multiple texts using one or more evaluators.\n');

  try {
    // Step 1: Get CSV file path — parse once inside validate, reuse result
    let inputs: BatchInput[] = [];
    const { csvPath } = await prompts({
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

    if (!csvPath) {
      console.log('No file path provided. Run the command again to start over.');
      process.exit(0);
    }

    console.log(`\n✓ Found ${inputs.length} rows in CSV\n`);

    // Step 2: Display the evaluator group that will run
    // (Only one group currently; when more are added this becomes a selection prompt)
    const group = getAvailableGroups()[0];
    console.log(`✓ Evaluator group: ${group.name}`);
    console.log(`  ${group.description}\n`);

    // Enforce row limit before asking for API keys (unless bypass is opted in)
    if (inputs.length > group.maxInputRows) {
      if (cliArgs.bypassRowLimit) {
        console.warn(`⚠️  Row limit bypassed: ${inputs.length} rows (default max ${group.maxInputRows}).`);
        console.warn(`   Expect longer runtime and possible provider throttling.\n`);
      } else {
        console.error(`❌ Too many rows: ${inputs.length} (max ${group.maxInputRows} for this group)\n`);
        console.log('Suggestions:');
        console.log(`  • Trim the CSV to ${group.maxInputRows} rows`);
        console.log('  • Split into multiple smaller batches');
        console.log('  • Re-run with --bypass-row-limit to skip this check (use with caution)\n');
        process.exit(1);
      }
    }

    // Step 3: Get API keys required by this group
    let googleApiKey: string | undefined;
    let openaiApiKey: string | undefined;

    if (group.requiresGoogleKey) {
      const result = await prompts({
        type: 'password',
        name: 'key',
        message: 'Google API Key:',
        initial: process.env.GOOGLE_API_KEY || '',
        validate: (value) => (value ? true : 'Google API key is required'),
      });

      if (!result.key) {
        console.log('Cancelled.');
        process.exit(0);
      }

      googleApiKey = result.key;
    }

    if (group.requiresOpenAIKey) {
      const result = await prompts({
        type: 'password',
        name: 'key',
        message: 'OpenAI API Key:',
        initial: process.env.OPENAI_API_KEY || '',
        validate: (value) => (value ? true : 'OpenAI API key is required'),
      });

      if (!result.key) {
        console.log('Cancelled.');
        process.exit(0);
      }

      openaiApiKey = result.key;
    }

    // Step 4: Get output directory (with human-readable timestamp in local time)
    const now = new Date();
    const pad = (n: number) => String(n).padStart(2, '0');
    const timestamp = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
    const defaultOutputDir = path.join(process.cwd(), `batch-results-${timestamp}`);

    const { outputDir } = await prompts({
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

    if (!outputDir) {
      console.log('No output directory provided. Run the command again to start over.');
      process.exit(0);
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
    console.log(`  Input rows: ${inputs.length}${cliArgs.bypassRowLimit ? ' (row limit bypassed)' : ''}`);
    console.log(`  Evaluators: ${group.evaluatorIds.length}`);
    console.log(`  Total tasks: ${totalTasks}`);
    console.log(`  Concurrency: ${cliArgs.concurrency ?? 3}`);
    console.log(`  Max retries: ${cliArgs.maxRetries ?? 2}`);
    console.log(`  Output: ${outputDir}\n`);

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
      googleApiKey,
      openaiApiKey,
      concurrency: cliArgs.concurrency ?? 3,
      maxRetries: cliArgs.maxRetries ?? 2,
      telemetry: !cliArgs.noTelemetry,
      bypassRowLimit: cliArgs.bypassRowLimit ?? false,
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

      // Open the HTML report in the default browser
      const htmlPath = path.join(outputDir, 'results.html');
      try {
        const cmd = process.platform === 'win32' ? `start "" "${htmlPath}"` : `open "${htmlPath}"`;
        exec(cmd);
      } catch {
        // Non-fatal — report is still saved
      }
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
