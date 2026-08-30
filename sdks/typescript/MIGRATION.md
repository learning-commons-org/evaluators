# Migrating from 0.8.0 to 1.0.0

1.0.0 moves every evaluator onto the shared, language-neutral contracts under `evals/`, so the SDK reads its models, prompts, grades, inputs and output shapes from the same declarations the Python SDK and the notebooks use. The payoff is that a result is now identical across our SDKs; the cost is that most of the public surface changed at once.

Twenty-six exported names are gone and seventy-three are new. Work through the sections below in order — the first four affect every caller.

## 1. `evaluate()` takes named inputs

Positional arguments are gone. Each evaluator declares its inputs in `input_schema.json`, and those names are the argument keys.

```diff
- await evaluator.evaluate(text, "5");
+ await evaluator.evaluate({ text, grade_level: "5" });
```

Input names by family:

| Family | Inputs |
| --- | --- |
| Text complexity (7 evaluators) | `{ text, grade_level }` |
| `GradeLevelAppropriatenessEvaluator` | `{ text }` |
| Feedback (7 evaluators) | `{ student_text, feedback_text }` |
| `MathStandardsAlignmentEvaluator` | `{ question, statementCode, jurisdiction }` |

Unknown keys, missing keys and out-of-range values now throw `InputValidationError` before any model runs. Text is bounded at 1–10,000 characters, measured as you sent it.

## 2. The result envelope changed shape

```diff
- interface EvaluationResult<TScore, TInternal> {
-   score: TScore;
-   reasoning: string;
-   metadata: EvaluationMetadata;
-   _internal?: TInternal;
- }
+ interface EvaluationResult<TResult> {
+   evaluator: string;   // the registry id
+   result: TResult;     // the payload, exactly as output_schema.json declares it
+   metadata: EvaluationMetadata;
+ }
```

There is no hoisted `score` and no `_internal`. The payload is the model's structured output with keys and values unaltered, which is what makes it byte-identical across SDKs.

```diff
- const { score, reasoning, _internal } = await evaluator.evaluate(text, "5");
+ const { result } = await evaluator.evaluate({ text, grade_level: "5" });
+ const { complexity_score, reasoning } = result;
```

If you had generic code over several evaluators that relied on `score`, use `readOutcome`, which reads whichever fields the contract nominates as the verdict and its rationale:

```typescript
import { readOutcome } from "@learning-commons/evaluators";

const evaluation = await evaluator.evaluate({ text, grade_level: "5" });
const { score, reasoning } = readOutcome(evaluation, MyEvaluator.metadata.outcome);
```

`score` is stringified, and is `undefined` for an evaluator whose output is not a single judgement.

**Token counts moved** into a nested object:

```diff
- metadata.inputTokens;
- metadata.outputTokens;
+ metadata.tokenUsage.inputTokens;
+ metadata.tokenUsage.outputTokens;
```

## 3. Evaluators renamed onto the taxonomy

| 0.8.0 | 1.0.0 |
| --- | --- |
| `SmkEvaluator` / `evaluateSmk` | `BackgroundKnowledgeDemandsEvaluator` / `evaluateBackgroundKnowledgeDemands` |
| `ConventionalityEvaluator` / `evaluateConventionality` | `MeaningDirectnessEvaluator` / `evaluateMeaningDirectness` |
| `PurposeEvaluator` / `evaluatePurpose` | `PurposeClarityEvaluator` / `evaluatePurposeClarity` |
| `VocabularyEvaluator` / `evaluateVocabulary` | `VocabularyComplexityEvaluator` / `evaluateVocabularyComplexity` |
| `<Evaluator>Internal` types | `<Evaluator>Result` |
| `GradeLevelAppropriatenessSchema` | `GradeLevelAppropriatenessOutputSchema` |
| `Providers` | `Provider` |

`TextComplexityEvaluator`, `evaluateTextComplexity`, `TextComplexityResult` and `TextComplexityLevel` are **removed with no replacement.** The composite ran several evaluators and merged their verdicts, which hid which model produced what. Call the evaluators you want and combine the results yourself, or use the `text-complexity` batch family, which does this with a report.

## 4. Errors are grouped by fault domain

`EvaluatorError` is still the root, but the middle of the hierarchy is new — you can now catch by who is at fault.

| 0.8.0 | 1.0.0 |
| --- | --- |
| `ValidationError` | `InputValidationError` |
| `TimeoutError` | `RequestTimeoutError` |
| `APIError` | **removed** — catch `DependencyError` instead |

`AuthenticationError`, `RateLimitError` and `NetworkError` kept their names but now extend `DependencyError` rather than `APIError`. `KnowledgeGraphError` also moved under `DependencyError`.

One reparenting is easy to miss: **`StandardNotFoundError` now extends `InputValidationError`**, not `KnowledgeGraphError`. A code that does not resolve is a bad input, not an upstream failure, so a `catch (e) { if (e instanceof KnowledgeGraphError) ... }` that used to see it no longer will.

New: `DependencyError`, `LLMProviderError`, `LLMOutputProcessingError` (an `EvaluationError`, for a response that arrived but could not be used).

## 5. `grade` is `gradeLevel` everywhere

The word "grade" meant three things across the API, the Knowledge Graph boundary and the batch CSV. It is now `gradeLevel` in camelCase contexts and `grade_level` in the wire and CSV formats.

- Evaluator input: `grade` → `grade_level`
- Result and report fields: `grade` → `gradeLevel`
- Batch CSV column: `grade` → `grade_level` — **existing input files need the header renamed**

## 6. The Learning Commons key is one option

```diff
- new MathStandardsAlignmentEvaluator({ platformApiKey: key });
- new SomeEvaluator({ partnerKey: key });
+ new MathStandardsAlignmentEvaluator({ learningCommonsApiKey: key });
```

Both `partnerKey` and `platformApiKey` are gone. `learningCommonsApiKey` on the evaluator config authorizes Learning Commons API calls such as the Knowledge Graph. Identified telemetry is a separate, opt-in setting: `telemetry: { learningCommonsApiKey: key }`.

## 7. Peer dependencies moved a major version

```bash
npm install ai@^7 @ai-sdk/google@^4 @ai-sdk/openai@^4 @ai-sdk/anthropic@^4
```

| Peer | 0.8.0 | 1.0.0 |
| --- | --- | --- |
| `ai` | `>=6.0.0` | `>=7.0.0` |
| `@ai-sdk/google`, `@ai-sdk/openai`, `@ai-sdk/anthropic` | `>=3.0.0` | `>=4.0.0` |

Node's minimum is unchanged at `>=20.19.0`.

## 8. Math standards alignment returns the envelope

It was the last evaluator returning its payload bare.

```diff
- const alignment = await evaluator.evaluate({ ... });
- console.log(alignment.alignedCount);
+ const { result } = await evaluator.evaluate({ ... });
+ console.log(result.alignedCount);
```

`evaluateItems` and `evaluateByGradeLevel` are unchanged: one call fans out over many question × standard pairs, so there is no single model or duration to report.

## 9. Smaller behaviour changes

- **`metadata.supportedGrades`** now reports what the contract says the evaluator targets. Previously it was derived from the grade input's enum, so the seven feedback evaluators and Grade Level Appropriateness published `[]`. It is not a validation set — where a `grade_level` input exists, its schema enum is what rejects a bad value.
- **Vocabulary Complexity** reports the model that actually ran for grades 3–4, which differs from the 5–12 branch. If you asserted one model string for all grades, it will now differ.
- **Grade Level Appropriateness and Sentence Structure** emit exactly the fields their contracts declare. GLA returns `grade_band`, `alternative_grade_band`, `scaffolding_needed`, `reasoning`.
- **The three complexity-score schemas** are generated from their contracts, so field descriptions and enum values follow the contract rather than a hand-written copy.

## What is new in 1.0.0

- **Seven feedback evaluators** judging teacher comments on student writing, and `OrganizationalStructureEvaluator` and `ReferenceKnowledgeDemandsEvaluator` are now public.
- **`llmProvider`** — bring your own provider. Inject any `LLMProvider` and no API keys are needed, for Vertex AI, Bedrock, a gateway or an eval framework's model system. Mutually exclusive with `modelOverride`.
- **The `feedback` batch family**, alongside `text-complexity` and `math-standards-alignment`.
- **`getEvaluators()` / `getEvaluator(id)`** — a registry over all sixteen, for enumeration and
  for resolving a stored result's id back to the evaluator that produced it. Renamed ids
  resolve through `idHistory`, so a result written under an old name stays identifiable.

The `@learning-commons/evaluators/batch` entry point and the `evaluators-batch` command both existed in 0.8.0; they are documented in the [README](./README.md) now, which is the change.
