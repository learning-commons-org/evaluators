# Batch CSV Evaluator

Evaluate rows from a CSV file with an **evaluator family**, writing results as CSV and JSON, plus HTML for the families that have a report.

## Evaluator families

A *family* is a set of evaluators that share an input contract, credential needs, and report shape. Each run targets one family; you may run all of its members or a subset.

| Family (`--family`) | Members | Required CSV columns | Keys | Max rows |
| --- | --- | --- | --- | --- |
| `text-complexity` | student_facing_text.ela_reading.grade_level_appropriateness, student_facing_text.ela_reading.background_knowledge_demands, student_facing_text.ela_reading.vocabulary_complexity, student_facing_text.ela_reading.sentence_structure, student_facing_text.ela_reading.meaning_directness, student_facing_text.ela_reading.purpose_clarity, student_facing_text.ela_reading.organizational_structure, student_facing_text.ela_reading.reference_knowledge_demands | `text`, `grade_level` | Google + OpenAI | 50 |
| `feedback` | feedback.ela_writing.revision_accuracy, feedback.ela_writing.revision_actionability, feedback.ela_writing.revision_manageability, feedback.ela_writing.strength_acknowledgment, feedback.ela_writing.student_response_specificity, feedback.ela_writing.tone_appropriateness, feedback.ela_writing.withholding_answers | `student_text`, `feedback_text` | OpenAI | 50 |
| `math-standards-alignment` | academic_standards_alignment.mathematics.math_standards_alignment | `question` (alias: `text`), `statement_code` (aliases: `statementCode`, `ccss_standard`, `standard`); optional `jurisdiction` (default `Multi-State`), `grade_level`, `id` (alias: `item_id`) | Anthropic + Learning Commons (Knowledge Graph) | 5000 |

Column matching is case-insensitive and alias-aware; the canonical column wins when both it and an alias are present.

`getFamily(id)` is authoritative for all of the above — `.members`, `.columns` and `.maxInputRows` come straight from the family definition. `--bypass-row-limit` lifts the row cap.

`text-complexity` includes Grade Level Appropriateness, which determines a grade rather than judging against one, so it ignores the required `grade_level` column that the other seven members need. Use `--evaluator` to run a subset.

## Usage

```bash
# Interactive: prompts for family, members, model, keys, output dir
evaluators-batch

# Non-interactive (CI): every input supplied up front, never prompts
evaluators-batch corpus.csv \
  --family math-standards-alignment \
  --learning-commons-api-key "$LEARNING_COMMONS_API_KEY" \
  --anthropic-api-key "$ANTHROPIC_API_KEY" \
  --output-dir ./out --yes

# Run only some members of a family (avoids paying for evaluators you don't need)
evaluators-batch texts.csv --family text-complexity --evaluator student_facing_text.ela_reading.vocabulary_complexity --yes

# Model override: a shortcode (haiku, opus) or provider:model
evaluators-batch texts.csv --family text-complexity --model anthropic:claude-opus-4-8 --yes

# Feedback quality over a CSV of student/feedback pairs
evaluators-batch comments.csv --family feedback --openai-api-key "$OPENAI_API_KEY" --yes
```

`-y`/`--yes` (or the absence of a TTY, e.g. CI) enables non-interactive mode: no prompts, and a clear error on any missing required input. Each run writes `results.csv` and `results.json`; `text-complexity` and `math-standards-alignment` also write `results.html`. The `math-standards-alignment` report is a verdict browser (per-item aligned/total with expandable per-component reasoning); the JSON carries full per-component detail plus each row's original columns so results join back to the source corpus.

### Options

| Flag | Default | Purpose |
| --- | --- | --- |
| `--family <id>` | prompted | Which family to run |
| `--evaluator <id[,id...]>` | all members | Run a subset of the family (repeatable) |
| `--model <alias\|provider:model>` | each evaluator's contract | Override the model for all members; shortcodes `haiku`, `opus` |
| `--google-api-key` / `--openai-api-key` / `--anthropic-api-key` / `--learning-commons-api-key` | matching env var | Provider and Learning Commons credentials; the flag wins over the env var |
| `--output-dir <path>` | `./batch-results-<timestamp>` | Where results are written |
| `--concurrency <n>` | 3 | Max parallel evaluations |
| `--max-retries <n>` | 2 | Retries per failed call |
| `--bypass-row-limit` | off | Skip the per-family row cap |
| `--no-telemetry` | telemetry on | Disable usage telemetry |
| `-y`, `--yes` | off | Non-interactive: never prompt, error on missing input |
| `--version` / `--help` | — | Print version / full flag list |

Unlike the SDK, the CLI reads credentials from the environment when the matching flag is absent.

Run `evaluators-batch --help` for the authoritative flag list.

### Non-standard input formats

The CLI consumes a generic CSV. If your source data is in another shape (JSON Lines, a bespoke schema, items whose question text must be assembled from multiple fields), convert it to the generic CSV first with a small one-off script — keep that converter outside this package.

## Programmatic API

`@learning-commons/evaluators/batch` is the same engine without the command. It **returns** results; it writes nothing.

```typescript
import { BatchEvaluator, parseCSV } from "@learning-commons/evaluators/batch";

const rows = parseCSV("./input.csv"); // a path, not CSV text

const output = await new BatchEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
  concurrency: 3,
}).evaluate(rows, "text-complexity", {
  onProgress: (result) => console.log(result.evaluatorId, result.status),
});

console.log(`${output.summary.successful}/${output.summary.totalTasks} succeeded`);
```

### Inspecting families

`getFamilies()` lists the three; `getFamily(id)` gives one family's members, column spec and row limit before you run:

```typescript
getFamilies().map((f) => f.id);            // ["text-complexity", "math-standards-alignment", "feedback"]
getFamily("feedback").members.length;      // 7
getFamily("text-complexity").columns;      // [{ name, required, aliases?, default? }, ...]
getFamily("text-complexity").maxInputRows; // 50
```

### Formatting results

`renderOutputs` produces the same files the command writes:

```typescript
import { renderOutputs, type ReportMeta } from "@learning-commons/evaluators/batch";

const meta: ReportMeta = {
  csvPath: "./input.csv",      // recorded in the report header
  groupId: "text-complexity",  // the family id
  reportId: "run-2026-08-31",
  generatedAt: new Date(),
  totalInputRows: rows.length,
};

const { csv, json, html } = renderOutputs("text-complexity", output, meta);
```

`html` is absent for families without a report of their own. `formatAsCSV(output)`, `formatAsJSON(output, meta)` and `formatAsHTML(output, meta)` are the individual projections.

Those outputs are a flattened per-row summary — score, reasoning and status — not the full payloads, and their shape differs between the standards family and the others. For full payloads, call the evaluators directly.

## Installation

```bash
# Install globally
npm install -g @learning-commons/evaluators

# Or run directly with npx
npx evaluators-batch
```

Either form runs interactively from any directory when given no arguments.

## Documentation

For more implementation details, visit [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/typescript/batch-evaluator).

---

## Development & Testing

### Local development

Before publishing the SDK package, run the batch CLI directly:

```bash
cd sdks/typescript
npm run build # Build project
node dist/batch/cli.js # Run the CLI command directly
```

### Local testing

```bash
# Build and pack
# Creates: learning-commons-evaluators-x.x.x.tgz
npm run build && npm pack

# Test installation in another directory
cd /tmp
npm install /path/to/learning-commons-evaluators-x.x.x.tgz
evaluators-batch
```
