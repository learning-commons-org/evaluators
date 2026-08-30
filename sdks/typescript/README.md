# @learning-commons/evaluators

[![npm version](https://img.shields.io/npm/v/@learning-commons/evaluators)](https://www.npmjs.com/package/@learning-commons/evaluators)

TypeScript SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction) — sixteen LLM-backed evaluators for the complexity of text students read, the quality of feedback they receive, and the alignment of math items to standards.

Requires Node >= 20.19.0.

## Installation

Install the `@learning-commons/evaluators` and [Vercel AI](https://sdk.vercel.ai) SDKs:

```bash
npm install @learning-commons/evaluators ai
```

Next, install the provider adapter(s) for the evaluators you plan to run — the table below gives each evaluator's provider:

```bash
npm install @ai-sdk/openai     # OpenAI
npm install @ai-sdk/google     # Google Gemini
npm install @ai-sdk/anthropic  # Anthropic
```

## Quickstart

```typescript
import { GradeLevelAppropriatenessEvaluator } from "@learning-commons/evaluators";

const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

const { result, metadata } = await evaluator.evaluate({
  text: "The cat's out of the bag now.",
});

console.log(result.grade_band); // a CCSS band, e.g. "2-3"
console.log(result.alternative_grade_band); // the band reachable with scaffolding
console.log(result.scaffolding_needed); // what that band would need
console.log(metadata.model); // "google:gemini-3.6-flash"
```

Every evaluator resolves to the same three-part envelope, so generic code works across all sixteen:

```typescript
{
  evaluator: string;   // registry id, e.g. "student_facing_text.ela_reading.vocabulary_complexity"
  result: TResult;     // the evaluator's own payload, exactly as its output schema declares it
  metadata: {
    model: string;             // "provider:model" for the model that actually ran
    processingTimeMs: number;
    tokenUsage: { inputTokens: number; outputTokens: number };
  };
}
```

`result` is the model's structured output with keys and values unaltered, so the payload is identical across our SDKs. When you need one comparable value per evaluation regardless of evaluator, use `readOutcome`:

```typescript
import { readOutcome, VocabularyComplexityEvaluator } from "@learning-commons/evaluators";

const evaluation = await new VocabularyComplexityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
}).evaluate({ text, grade_level: "5" });

const { score, reasoning } = readOutcome(evaluation, VocabularyComplexityEvaluator.metadata.outcome);
```

## Evaluators

Text complexity — how demanding a text is for a given grade. Each takes `{ text, grade_level }` and returns a `complexity_score` on a four-level scale — `slightly_complex`, `moderately_complex`, `very_complex`, `exceedingly_complex` — with `reasoning`. Purpose Clarity can also answer `more_context_needed`.

| Evaluator | Grades | Provider | Docs |
| --- | --- | --- | --- |
| `BackgroundKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/subject-matter-knowledge/about-this-evaluator) |
| `MeaningDirectnessEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator) |
| `OrganizationalStructureEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/organizational-structure) |
| `PurposeClarityEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/purpose/about-this-evaluator) |
| `ReferenceKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/intertextuality) |
| `SentenceStructureEvaluator` | 3–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/sentence-structure-evaluator/about-this-evaluator) |
| `VocabularyComplexityEvaluator` | 3–12 | Google + OpenAI | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator) |

Grade band — takes `{ text }` only, and determines the grade rather than judging against one. Returns `grade_band`, `alternative_grade_band`, `scaffolding_needed`, `reasoning`. Bands are `K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-12` — spans on the CCSS text-complexity scale, not single grades.

| Evaluator | Grades | Provider | Docs |
| --- | --- | --- | --- |
| `GradeLevelAppropriatenessEvaluator` | K–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/grade-level-appropriateness-evaluator/about-this-evaluator) |

Feedback quality — judges a teacher comment on a student's writing. Each takes `{ student_text, feedback_text }` and returns a binary `quality_score` with `reasoning`, `key_features` and `proposed_adjustment`.

| Evaluator | Grades | Provider |
| --- | --- | --- |
| `RevisionAccuracyEvaluator` | 6–12 | OpenAI |
| `RevisionActionabilityEvaluator` | 6–12 | OpenAI |
| `RevisionManageabilityEvaluator` | 6–12 | OpenAI |
| `StrengthAcknowledgmentEvaluator` | 6–12 | OpenAI |
| `StudentResponseSpecificityEvaluator` | 6–12 | OpenAI |
| `ToneAppropriatenessEvaluator` | 6–12 | OpenAI |
| `WithholdingAnswersEvaluator` | 6–12 | OpenAI |

Standards alignment — checks a math item against a standard, component by component.

| Evaluator | Grades | Provider | Also needs |
| --- | --- | --- | --- |
| `MathStandardsAlignmentEvaluator` | K–12 | Anthropic | `learningCommonsApiKey` (Knowledge Graph) |

```typescript
import { MathStandardsAlignmentEvaluator, Jurisdiction } from "@learning-commons/evaluators";

const { result } = await new MathStandardsAlignmentEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  learningCommonsApiKey: process.env.LEARNING_COMMONS_API_KEY,
}).evaluate({
  question: "A playground is shaped like an L. What is its area?",
  statementCode: "3.MD.C.7.d",
  jurisdiction: Jurisdiction.MultiState,
});

console.log(`${result.alignedCount}/${result.totalCount} learning components aligned`);
```

Each evaluator is also available as a function — `evaluateGradeLevelAppropriateness(input, config)` and so on — for callers who would rather not hold an instance.

## Configuration

Every evaluator takes the same options:

| Option | Purpose |
| --- | --- |
| `googleApiKey` / `openaiApiKey` / `anthropicApiKey` | Keys for the providers the evaluator uses |
| `learningCommonsApiKey` | Authorizes Learning Commons API calls, such as the Knowledge Graph |
| `modelOverride` | Run every call on a different `{ provider, model }` |
| `llmProvider` | Bring your own provider (see below) |
| `maxRetries` | Retries per failed call (default 2, so 3 attempts) |
| `telemetry` | `true`, `false`, or `TelemetryOptions` (default on, without input recording) |
| `logger` / `logLevel` | Inject a logger, or set the console logger's level (default `WARN`) |

### Bring your own provider

Pass any object implementing `LLMProvider` and the evaluator routes every call through it, skipping the built-in API-key adapters entirely — useful for Google Vertex AI, Amazon Bedrock, an AI-SDK gateway, or an eval framework's model system. No provider API keys are needed, and any ambient ones go unused.

```typescript
const evaluator = new SentenceStructureEvaluator({ llmProvider: myProvider });
```

It is mutually exclusive with `modelOverride`: setting both throws `ConfigurationError`.

## Batch

`@learning-commons/evaluators/batch` runs a CSV of rows through a family of evaluators, with concurrency, retries, and CSV/JSON/HTML output.

```typescript
import { BatchEvaluator, getFamily, parseCSV } from "@learning-commons/evaluators/batch";
```

The same thing is available as a command, installed as `evaluators-batch`:

```bash
npx evaluators-batch input.csv --family text-complexity --output-dir ./results
npx evaluators-batch --help
```

## Errors

Errors are grouped by fault domain, so you can catch by who is at fault rather than by individual failure. All extend `EvaluatorError`.

| Class | Meaning |
| --- | --- |
| `ConfigurationError` | The SDK was set up wrong — missing key, conflicting options, a model the provider rejects |
| `InputValidationError` | The input was rejected before any model ran; `StandardNotFoundError` is a subclass |
| `EvaluationError` | The evaluation ran but could not be completed; `LLMOutputProcessingError` is a subclass |
| `DependencyError` | Something the SDK depends on failed. Subclasses: `AuthenticationError`, `RateLimitError`, `NetworkError`, `RequestTimeoutError`, `LLMProviderError`, `KnowledgeGraphError` |

```typescript
try {
  await evaluator.evaluate({ text, grade_level: "5" });
} catch (error) {
  if (error instanceof RateLimitError) retryLater();
  else if (error instanceof DependencyError) reportUpstreamOutage(error);
  else if (error instanceof InputValidationError) fixTheRow(error);
  else throw error;
}
```

## Documentation

Full reference at [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview). Upgrading from 0.8.0? See [MIGRATION.md](./MIGRATION.md).

## License

MIT
