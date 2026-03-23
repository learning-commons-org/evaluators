# Batch CSV Evaluator

Evaluate multiple texts from a CSV file using a group of evaluators, with results output in CSV and HTML formats.

## Usage

### Installation

After publishing to npm:

```bash
# Install globally
npm install -g @learning-commons/evaluators

# Or run directly with npx
npx evaluators-batch
```

### Interactive Mode

Run the batch evaluator interactively from any directory:

```bash
# If installed globally
evaluators-batch

# Or with npx
npx evaluators-batch
```

**Important:** Run this command from the directory containing your CSV file, or provide an absolute path to your CSV.

The CLI will guide you through:
1. **CSV File Path**: Location of your input CSV file
2. **API Keys**: Enter required API keys (only prompted for keys the group requires)
3. **Output Directory**: Where to save results (default: timestamped folder in current directory)
4. **Confirmation**: Review summary before starting

The output directory is automatically created with a human-readable timestamp:
```
batch-results-2024-02-07_14-30-22/
├── results.csv
└── results.html
```

### Input CSV Format

Your CSV must have a `text` column and a `grade` column (both case-insensitive). Any additional columns are preserved as-is in the output.

Example `input.csv`:
```csv
text,grade
"The cat sat on the mat.",3
"Photosynthesis is the process by which plants convert sunlight into energy.",5
"The mitochondria are the powerhouse of the cell.",8
```

Any additional columns beyond `text` and `grade` are preserved as-is in the output.

### Evaluator Groups

The batch evaluator runs a fixed group of evaluators together. The current available group is:

- **text-complexity**: Runs grade-level appropriateness, subject matter knowledge, vocabulary complexity, sentence structure, and conventionality evaluators together (requires both Google and OpenAI API keys). Maximum 50 input rows. If you exceed the limit, the CLI will exit with an error and suggest splitting into smaller batches.

### Output Files

Two files are generated:

1. **CSV** (`results.csv`):
   - Spreadsheet-compatible format
   - Original CSV columns preserved, followed by `{evaluator}_score`, `{evaluator}_reasoning`, and `{evaluator}_status` columns for each evaluator

2. **HTML** (`results.html`):
   - Summary dashboard with grade-level distribution and text complexity charts
   - Full results table with per-evaluator scores and reasoning
   - Opens automatically in your default browser after evaluation completes

During evaluation, real-time progress is displayed:

```
Processing evaluations...
████████████░░░░░░░░ 60% (30/50)
  ✓ grade-level-appropriateness: 6/10 successful
  ✓ subject-matter-knowledge: 6/10 successful
  ✓ vocabulary: 6/10 successful
  ✓ sentence-structure: 6/10 successful
  ⏳ conventionality: 6/10 successful

⏱  Elapsed: 2m 15s | Estimated remaining: 1m 30s
```

### CLI Flags

You can override defaults by passing flags when running the command:

```bash
evaluators-batch --concurrency 5 --max-retries 3 --no-telemetry
```

| Flag | Default | Description |
|---|---|---|
| `--concurrency <n>` | `3` | Number of evaluations to run in parallel |
| `--max-retries <n>` | `2` | Number of times to retry a failed evaluation |
| `--no-telemetry` | telemetry on | Disable telemetry reporting |

### API Keys

You can provide API keys in two ways:
1. **Environment variables**: `GOOGLE_API_KEY`, `OPENAI_API_KEY` — used as defaults in the prompts
2. **Interactive prompts**: Enter when prompted (keys are masked)

### Graceful Shutdown

Press `Ctrl+C` during evaluation to gracefully shut down:

1. **In-flight tasks complete**: Running evaluations finish processing
2. **New tasks cancelled**: Pending tasks are skipped
3. **Partial results saved**: All completed results are saved to `results-partial.*` files
4. **Progress preserved**: No loss of work done so far

Example:
```bash
# Press Ctrl+C during a long batch evaluation

⚠️  Shutdown requested. Saving partial results...
   (Press Ctrl+C again to force quit)

✓ Saved 15 results to:
  ./batch-results-2024-02-07_14-30-22/
    ├── results-partial.csv
    └── results-partial.html
```

Press `Ctrl+C` twice to force quit immediately (not recommended — may lose in-flight results).

---

## Development & Testing

### Running Locally (Before Publishing)

```bash
# From the SDK root directory
cd sdks/typescript

# Build the project
npm run build

# Run the batch CLI directly
node dist/batch/cli.js
```

### Testing the Package Locally

```bash
# Build and pack
npm run build
npm pack
# Creates: learning-commons-evaluators-x.x.x.tgz

# Test installation in another directory
cd /tmp
npm install /path/to/learning-commons-evaluators-x.x.x.tgz
evaluators-batch
```
