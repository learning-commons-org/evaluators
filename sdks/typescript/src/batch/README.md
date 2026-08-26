# Batch CSV Evaluator

Evaluate rows from a CSV file with an **evaluator family**, writing results as CSV, JSON, and HTML.

## Evaluator families

A *family* is a set of evaluators that share an input contract, credential needs, and report shape. Each run targets one family; you may run all of its members or a subset.

| Family (`--family`) | Members | Required CSV columns | Keys |
| --- | --- | --- | --- |
| `text-complexity` | grade-level-appropriateness, subject-matter-knowledge, vocabulary, sentence-structure, conventionality, literacy.gla.purpose, literacy.gla.organizational_structure, literacy.gla.intertextuality | `text`, `grade` | Google + OpenAI |
| `math-standards-alignment` | math.standards-alignment | `question`, `statementCode` (aliases: `ccss_standard`, `text`); optional `jurisdiction` (default `Multi-State`), `grade`, `id` | Anthropic + **platform** (Knowledge Graph) |

Column matching is case-insensitive and alias-aware; the canonical column wins when both it and an alias are present.

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
evaluators-batch texts.csv --family text-complexity --evaluator vocabulary,conventionality --yes

# Model override: a shortcode (haiku, opus) or provider:model
evaluators-batch texts.csv --family text-complexity --model anthropic:claude-opus-4-8 --yes
```

`-y`/`--yes` (or the absence of a TTY, e.g. CI) enables non-interactive mode: no prompts, and a clear error on any missing required input. Each run writes `results.csv`, `results.json`, and `results.html` to the output directory. The `math-standards-alignment` report is a verdict browser (per-item aligned/total with expandable per-component reasoning); the JSON carries full per-component detail plus each row's original columns so results join back to the source corpus.

Run `evaluators-batch --help` for the full flag list.

### Non-standard input formats

The CLI consumes a generic CSV. If your source data is in another shape (JSON Lines, a bespoke schema, items whose question text must be assembled from multiple fields), convert it to the generic CSV first with a small one-off script — keep that converter outside this package.

## Installation

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
