# Batch CSV Evaluator

Evaluate multiple texts from a CSV file using a group of evaluators, with results output in CSV and HTML formats.

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
