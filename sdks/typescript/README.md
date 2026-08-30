# @learning-commons/evaluators

[![npm version](https://img.shields.io/npm/v/@learning-commons/evaluators)](https://www.npmjs.com/package/@learning-commons/evaluators)

TypeScript SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction) — sixteen LLM-backed evaluators for the complexity of text students read, the quality of feedback they receive, and the alignment of math items to standards.

Requires Node >= 20.19.0.

The SDK is ESM-first and the examples below use top-level `await`, so a TypeScript project
needs `"type": "module"` in `package.json`, `@types/node`, and:

```json
{
  "compilerOptions": {
    "module": "nodenext",
    "moduleResolution": "nodenext",
    "target": "es2022",
    "strict": true,
    "types": ["node"]
  }
}
```

You will also want the type packages:

```bash
npm install -D typescript @types/node @types/json-schema
```

`@types/json-schema` is needed because `ai`'s own dependency chain imports `json-schema`
untyped; without it `tsc` reports `TS7016` from inside `@ai-sdk/provider`, not from this
package. This SDK's declarations typecheck cleanly on their own, so `skipLibCheck` is not
required on their account — but adding it is the other way to silence that peer's gap.

CommonJS consumers can `require` the package but will need to rewrite the top-level `await`
in these snippets.

Each evaluator's argument and payload types are exported — `VocabularyComplexityInput`,
`VocabularyComplexityResult` and so on — so you can name them in your own signatures.

## Installation

Install the SDK alongside [Vercel AI](https://sdk.vercel.ai) and [zod](https://zod.dev):

```bash
npm install @learning-commons/evaluators ai zod
```

`ai` and `zod` are peer dependencies, so your project owns their versions. `zod` must be
version 4: the evaluator schemas this package exports are zod 4 values, and a second copy in
your tree makes them incompatible with your own — a mismatch that shows up as
`Type 'ZodObject<…>' is not assignable to type 'ZodTypeAny'` rather than as an install error.

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
    model: string;             // "provider:model" that ran; "a+b" when several did
    processingTimeMs: number;
    tokenUsage: { inputTokens: number; outputTokens: number };
  };
}
```

`result` is the model's structured output with keys and values unaltered, so the payload is identical across our SDKs. Payloads carry more than the verdict, and how much varies by evaluator: Background Knowledge
Demands returns `identified_topics`, `curriculum_check`, `assumptions_and_scaffolding` and
`friction_analysis`; Meaning Directness returns `conventionality_features`, `grade_context` and
`instructional_insights`; Organizational Structure, Purpose Clarity and Reference Knowledge
Demands each return a nested `details`; Vocabulary Complexity returns `tier_2_words`,
`tier_3_words`, `archaic_words` and `other_complex_words` as comma-joined strings. Only
Sentence Structure returns just the score and reasoning. Each evaluator exports its payload
type (`VocabularyComplexityResult` and so on) — that is the authoritative shape.

The feedback family's `quality_score` is the **number** `0` or `1`, and its `key_features` maps
each criterion to `{ met: 0 | 1, justification: string }` — `met` is a number, not a boolean.

`metadata.model` names every model that ran, joined by `+` when an evaluator uses more than one — so a multi-step evaluator reports e.g. `openai:gpt-4o-…+openai:gpt-4.1-…`. Which models run can also depend on the input: Vocabulary Complexity takes a different branch for grades 3-4 than for 5-12. The **Required key** column below is what you must supply, not a promise about which provider serves a given call. When you need one comparable value per evaluation regardless of evaluator, use `readOutcome`:

```typescript
import { readOutcome, VocabularyComplexityEvaluator } from "@learning-commons/evaluators";

const evaluation = await new VocabularyComplexityEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
}).evaluate({ text, grade_level: "5" });

const { score, reasoning } = readOutcome(evaluation, VocabularyComplexityEvaluator.metadata.outcome);
```

`score` is **always a string**, or `undefined` when the evaluator declares no single verdict.
That matters for the feedback family, whose verdict is the number `0` or `1`: `readOutcome`
returns `"0"`, and `"0"` is truthy in JavaScript. Compare explicitly — `score === "1"` — or read
the payload field directly (`evaluation.result.quality_score`, a real number) when you want
arithmetic. The second argument's type is exported as `DeclaredOutcome`, so you can write one
helper across several evaluators.

## Evaluators

Text complexity — how demanding a text is for a given grade. Each takes `{ text, grade_level }` and returns a `complexity_score` on a four-level scale — `slightly_complex`, `moderately_complex`, `very_complex`, `exceedingly_complex` — with `reasoning`. Purpose Clarity's `complexity_score` has a fifth possible value, `more_context_needed`, so a
switch over the four above will not be exhaustive for it.

| Evaluator | Grades | Required key | Docs |
| --- | --- | --- | --- |
| `BackgroundKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/subject-matter-knowledge/about-this-evaluator) |
| `MeaningDirectnessEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/conventionality/about-this-evaluator) |
| `OrganizationalStructureEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/organizational-structure) |
| `PurposeClarityEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/purpose/about-this-evaluator) |
| `ReferenceKnowledgeDemandsEvaluator` | 3–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/intertextuality) |
| `SentenceStructureEvaluator` | 3–12 | OpenAI | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/sentence-structure-evaluator/about-this-evaluator) |
| `VocabularyComplexityEvaluator` | 3–12 | Google + OpenAI | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/vocabulary-evaluator/about-this-evaluator) |

Grade band — takes `{ text }` only, and determines the grade rather than judging against one. Returns `grade_band`, `alternative_grade_band`, `scaffolding_needed`, `reasoning`. Bands are `K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-12` — spans on the CCSS text-complexity scale, not single grades.

| Evaluator | Grades | Required key | Docs |
| --- | --- | --- | --- |
| `GradeLevelAppropriatenessEvaluator` | K–12 | Google | [Link](https://docs.learningcommons.org/evaluators/literacy-evaluators/grade-level-appropriateness-evaluator/about-this-evaluator) |

Feedback quality — judges a teacher comment on a student's writing. Each takes `{ student_text, feedback_text }` and returns a binary `quality_score` with `reasoning`, `key_features` and `proposed_adjustment`.

| Evaluator | Grades | Required key |
| --- | --- | --- |
| `RevisionAccuracyEvaluator` | 6–12 | OpenAI |
| `RevisionActionabilityEvaluator` | 6–12 | OpenAI |
| `RevisionManageabilityEvaluator` | 6–12 | OpenAI |
| `StrengthAcknowledgmentEvaluator` | 6–12 | OpenAI |
| `StudentResponseSpecificityEvaluator` | 6–12 | OpenAI |
| `ToneAppropriatenessEvaluator` | 6–12 | OpenAI |
| `WithholdingAnswersEvaluator` | 6–12 | OpenAI |

Standards alignment — checks a math item against a standard, component by component.

| Evaluator | Grades | Required key | Also needs |
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

## Discovering evaluators

Every evaluator is listed in a registry, keyed by the registry id that appears on each result:

```typescript
import { getEvaluators, getEvaluator } from "@learning-commons/evaluators";

for (const { id, name, supportedGrades } of getEvaluators()) {
  console.log(`${name} (${id}) — grades ${supportedGrades.join(", ")}`);
}

// Renamed ids still resolve, so a stored result stays identifiable.
getEvaluator("conventionality")?.name; // "Meaning Directness Evaluator"
```

Both return metadata — `id`, `stableId`, `idHistory`, `name`, `description`, `supportedGrades`, `defaultProviders`, `requiredCredentials`, and `outcome` where the evaluator declares a single verdict. `requiredCredentials` lists only **non-LLM** services — it is `["learning_commons_api_key"]` for
math standards alignment and `[]` for the other fifteen, so it is not the answer to "which keys
does this need". Provider keys follow `defaultProviders`: `["google"]` means supply
`googleApiKey`. To *run* an evaluator, import it by name: the metadata does not tell you which named inputs it takes, and each evaluator's are different.

## Configuration

Every evaluator takes the same options:

| Option | Purpose |
| --- | --- |
| `googleApiKey` / `openaiApiKey` / `anthropicApiKey` | Keys for the providers the evaluator uses |
| `learningCommonsApiKey` | Authorizes Learning Commons API calls, such as the Knowledge Graph |
| `modelOverride` | Run every call on a different `{ provider, model }`; `provider` is the exported `Provider` enum |
| `llmProvider` | Bring your own provider (see below) |
| `maxRetries` | Retries per failed call (default 2, so 3 attempts) |
| `telemetry` | `true`, `false`, or `TelemetryOptions` (default on, without input recording) |
| `logger` / `logLevel` | Inject a logger, or set the console logger's level with the exported `LogLevel` enum (default `LogLevel.WARN`) |

`Provider` and `LogLevel` are enums, not strings — `provider: "google"` and
`logLevel: "ERROR"` do not compile. The members are `Provider.OpenAI`, `Provider.Google`,
`Provider.Anthropic`, and `LogLevel.DEBUG`, `INFO`, `WARN`, `ERROR`, `SILENT`:

```typescript
import { Provider, LogLevel, VocabularyComplexityEvaluator } from "@learning-commons/evaluators";

new VocabularyComplexityEvaluator({
  googleApiKey, openaiApiKey,
  modelOverride: { provider: Provider.Google, model: "gemini-2.5-flash" },
  logLevel: LogLevel.ERROR,
});
```

Keys are read from this object only. There is no environment-variable fallback: setting
`GOOGLE_API_KEY` in the environment does not satisfy `googleApiKey`, and omitting a key an
evaluator needs throws `ConfigurationError` at construction. (The `evaluators-batch` command
is the exception — it does read the environment, as its `--help` describes.)

### Bring your own provider

Pass any object implementing `LLMProvider` and the evaluator routes every call through it, skipping the built-in API-key adapters entirely — useful for Google Vertex AI, Amazon Bedrock, an AI-SDK gateway, or an eval framework's model system. No provider API keys are needed.

Three members are required, and the two methods are **not symmetrical**: `generateStructured`
takes one object and must return a `model`, while `generateText` takes positional arguments and
must not. `messages` includes the `system` turn, which most backends want as a separate
argument. A `temperature` of `null` means *send no temperature at all* — some models reject an
explicit value — so forward it conditionally rather than coercing it with `?? undefined`.

```typescript
import { generateText, Output } from "ai";
import { openai } from "@ai-sdk/openai";
import { SentenceStructureEvaluator, type LLMProvider, type Message } from "@learning-commons/evaluators";

/** `ai` takes the system turn as its own option; leaving it in `messages` is rejected. */
function split(messages: Message[]) {
  const system = messages.find((m) => m.role === "system");
  return {
    ...(system ? { system: system.content } : {}),
    messages: messages.filter((m) => m.role !== "system"),
  };
}

const myProvider: LLMProvider = {
  // "provider:model" — this is what the SDK reports as metadata.model.
  label: "byo:gpt-4o-mini",

  async generateStructured({ messages, schema, temperature }) {
    const started = Date.now();
    const { output, usage } = await generateText({
      model: openai("gpt-4o-mini"),
      ...split(messages),
      output: Output.object({ schema }),
      ...(temperature != null ? { temperature } : {}),
    });

    return {
      data: output,
      model: "gpt-4o-mini",
      usage: { inputTokens: usage.inputTokens ?? 0, outputTokens: usage.outputTokens ?? 0 },
      latencyMs: Date.now() - started,
    };
  },

  async generateText(messages, temperature) {
    const started = Date.now();
    const { text, usage } = await generateText({
      model: openai("gpt-4o-mini"),
      ...split(messages),
      ...(temperature != null ? { temperature } : {}),
    });

    return {
      text,
      usage: { inputTokens: usage.inputTokens ?? 0, outputTokens: usage.outputTokens ?? 0 },
      latencyMs: Date.now() - started,
    };
  },
};

const evaluation = await new SentenceStructureEvaluator({ llmProvider: myProvider }).evaluate({
  text: "The dog ran. It was fast. The children laughed at the sight of it.",
  grade_level: "5",
});
// evaluation.metadata.model === "byo:gpt-4o-mini"
```

`schema` is a Zod schema. `zod` is bundled with this package rather than being a peer, so a
backend that needs the schema in another form should convert it rather than expect a matching
`zod` of its own. An object missing any of the three members throws `ConfigurationError`.

It is mutually exclusive with `modelOverride`: setting both throws `ConfigurationError`.

## Batch

`@learning-commons/evaluators/batch` runs a CSV of rows through a family of evaluators, with concurrency and retries. It **returns** results; it writes nothing. Use `renderOutputs` to format them, or the command below, which writes the files for you.

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

`getFamily(id)` gives you a family's members and column spec if you need to inspect it first.

The same thing is available as a command, installed as `evaluators-batch`. This is what
writes `results.csv`, `results.json`, and — for `text-complexity` and
`math-standards-alignment` — `results.html`:

```bash
npx evaluators-batch input.csv --family text-complexity --output-dir ./results -y
npx evaluators-batch --help
```

`-y` makes it non-interactive: without it, it prompts for anything missing, which hangs a CI
job. Keys come from `--google-api-key` and friends or from the matching environment
variables. Each family has a row limit — 50 for `text-complexity` and `feedback`, 5000 for
`math-standards-alignment`, and `getFamily(id).maxInputRows` is authoritative.
`--bypass-row-limit` lifts it.

The CSV's columns depend on the family. `getFamily(id).columns` is authoritative:

| Family | Required columns | Optional |
| --- | --- | --- |
| `text-complexity` | `text`, `grade_level` | — |
| `feedback` | `student_text`, `feedback_text` | — |
| `math-standards-alignment` | `question` (or `text`), `statementCode` (or `statement_code`, `ccss_standard`, `standard`) | `jurisdiction` (default Multi-State), `grade_level`, `id` (or `item_id`) |

Those outputs are a flattened per-row summary — score, reasoning and status — not the full
payloads, and their shape differs between the standards family and the others. For full
payloads, call the evaluators directly.

## Errors

Errors are grouped by fault domain, so you can catch by who is at fault rather than by individual failure. All extend `EvaluatorError`.

| Class | Meaning |
| --- | --- |
| `ConfigurationError` | The SDK was set up wrong — missing key, conflicting options, a model the provider rejects |
| `InputValidationError` | The input was rejected before any model ran; `StandardNotFoundError` is a subclass |
| `EvaluationError` | The evaluation ran but could not be completed; `LLMOutputProcessingError` is a subclass |
| `DependencyError` | Something the SDK depends on failed. Subclasses: `AuthenticationError`, `RateLimitError`, `NetworkError`, `RequestTimeoutError`, `LLMProviderError`, `KnowledgeGraphError` |

A failed evaluation is also logged before it is thrown, so a caught error still prints an
`[ERROR]` block at the default level. Pass `logLevel: LogLevel.SILENT` if you would rather
report failures yourself.

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

Full reference at [our docs site](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview). Upgrading from an earlier major version? See [MIGRATION.md](./MIGRATION.md).

## License

MIT
