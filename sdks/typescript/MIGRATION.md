# Migrating from 0.8.0 to 1.0.0

1.0.0 moves every evaluator onto the shared, language-neutral contracts under `evals/`, so the SDK reads its models, prompts, grades, inputs and output shapes from the same declarations the Python SDK and the notebooks use. The payoff is that a result is now identical across our SDKs; the cost is that most of the public surface changed at once.

Twenty-six exported names are gone and seventy-three are new. Work through the sections below in order — the first four affect every caller.

## 0. Upgrade the package and the peers together

The peer ranges moved a major version, so installing the SDK on its own fails before you can
change a line of code:

```
npm error ERESOLVE unable to resolve dependency tree
npm error Found: ai@6.0.271
```

One command, not two:

```bash
npm install @learning-commons/evaluators@^1 zod@^4 ai@^7 @ai-sdk/google@^4 @ai-sdk/openai@^4 @ai-sdk/anthropic@^4
```

Install only the adapters you use. Node's floor is unchanged, but the range is now
`^20.19.0 || >=22.12.0`: the CommonJS build requires ESM-only packages, so it needs
`require(esm)`, which 20.19 has and 21.x / 22.0-22.11 do not.

**`zod` is now a peer dependency and must be added.** In 0.8.0 it was bundled, so npm
installed a copy for us; now your project declares it, which is what guarantees there is only
one copy.

It must be **version 4** — the exported evaluator schemas are zod 4 values. A project on zod 3
fails the install rather than the build:

```
npm error ERESOLVE unable to resolve dependency tree
npm error Found: zod@3.25.76
```

That is the intended outcome: it names the problem before any code runs. Bypassing it with
`--legacy-peer-deps` or `--force` installs zod 3 anyway, and the build then fails on our
declarations — `Namespace '…/zod/v3/external' has no exported member 'core'`.

For contrast, 0.8.0 gave **no** install-time signal: it bundled its own zod 4 alongside your
zod 3, and the two copies were structurally different types, so composing one of our schemas
with your own failed at your call site with nothing fixable there:

```
error TS2322: Type 'ZodObject<…, $strict>' is not assignable to type 'ZodTypeAny'.
  missing the following properties from type 'ZodType<any, any, any>': _type, _parse, …
```

That silent-two-copies state is what this change removes.

Note that `ai@7` accepts `zod@^3.25.76 || ^4.1.8`, so a project pinned to zod 3 for `ai`'s
sake now has to move to zod 4.

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
| `MathStandardsAlignmentEvaluator` | `{ question, statement_code, jurisdiction }` |

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

`score` is stringified, and is `undefined` for an evaluator whose output is not a single
judgement. `reasoning` is always a `string` — empty rather than absent — so it needs no
optional handling. `metadata.tokenUsage.inputTokens` and `outputTokens` are likewise always
present numbers.

Writing one helper across several evaluators — the case this replaces — needs a name for that
second argument. It is exported as `DeclaredOutcome`:

```typescript
import { readOutcome, type DeclaredOutcome, type EvaluationResult } from "@learning-commons/evaluators";

function toRow(dimension: string, evaluation: EvaluationResult, outcome: DeclaredOutcome | undefined) {
  const { score, reasoning } = readOutcome(evaluation, outcome);
  return { dimension, score, reasoning };
}
```

**Token counts moved** into a nested object:

```diff
- metadata.inputTokens;
- metadata.outputTokens;
+ metadata.tokenUsage.inputTokens;
+ metadata.tokenUsage.outputTokens;
```

## 2a. The verdict *values* changed — check your stored data

Nothing in the compiler will tell you about this, because `readOutcome` returns `score:
string`. Every complexity verdict changed case and separator, and the top grade band was
relabelled:

| | 0.8.0 | 1.0.0 |
| --- | --- | --- |
| complexity score | `"Slightly complex"` | `"slightly_complex"` |
| | `"Moderately complex"` | `"moderately_complex"` |
| | `"Very complex"` | `"very_complex"` |
| | `"Exceedingly complex"` | `"exceedingly_complex"` |
| Purpose Clarity's fifth value | `"More context needed"` | `"more_context_needed"` |
| top grade band | `"11-CCR"` | `"11-12"` |

The other bands (`K-1`, `2-3`, `4-5`, `6-8`, `9-10`) are unchanged, and the feedback family's
`0`/`1` is unchanged.

So `if (score === "Very complex")` silently stops matching, a dashboard filter silently returns
nothing, and a `GROUP BY score` silently splits into old and new buckets. **Grep for the old
strings, and backfill anything you have persisted.** Values now come straight from each
evaluator's contract, which is what makes them identical across our SDKs.

## 2b. Declared input values are literal unions

You will meet this while doing section 1, not separately. 0.8.0 took the grade as a positional
`string`; 1.0 takes it as a named input typed to the union its contract declares, generated
from the same file the runtime check reads:

```diff
- await evaluator.evaluate(text, grade);            // grade: string
+ await evaluator.evaluate({ text, grade_level: grade });
//                                        ^ '3' | '4' | … | '12'
```

So a typo that used to compile and fail at run time on a paid call is now a compile error.

Passing a literal is unaffected. **Passing the `string` variable you already had no longer
compiles** — which, since 0.8.0 typed it `string`, is most of what you are converting:

```typescript
const grade: string = row.grade_level;
await evaluator.evaluate({ text, grade_level: grade });
//                                            ^ string is not assignable
```

Narrow it where the external value enters your system:

```typescript
const GRADES = ['3', '4', '5', '6', '7', '8', '9', '10', '11', '12'] as const;
type Grade = (typeof GRADES)[number];

function toGrade(value: string): Grade {
  if (!GRADES.includes(value as Grade)) throw new Error(`Unsupported grade: ${value}`);
  return value as Grade;
}
```

Only declared enums changed. Text inputs remain `string` — their length bounds are not
expressible in the type system and stay with the run-time check. The affected fields are
`grade_level` on the seven text-complexity evaluators; math's `jurisdiction` was already the
`Jurisdiction` enum.

## 3. Evaluators renamed onto the taxonomy

| 0.8.0 | 1.0.0 |
| --- | --- |
| `SmkEvaluator` / `evaluateSmk` | `BackgroundKnowledgeDemandsEvaluator` / `evaluateBackgroundKnowledgeDemands` |
| `ConventionalityEvaluator` / `evaluateConventionality` | `MeaningDirectnessEvaluator` / `evaluateMeaningDirectness` |
| `PurposeEvaluator` / `evaluatePurpose` | `PurposeClarityEvaluator` / `evaluatePurposeClarity` |
| `VocabularyEvaluator` / `evaluateVocabulary` | `VocabularyComplexityEvaluator` / `evaluateVocabularyComplexity` |
| `<Evaluator>Internal` types | `<Evaluator>Result` |
| `GradeLevelAppropriatenessSchema` | `GradeLevelAppropriatenessOutputSchema` |
| `evaluator.evaluateByGrade(...)` | `evaluator.evaluateByGradeLevel(...)` |
| `GradeBand` as a **value** (it was a Zod enum, so `GradeBand.options` worked) | type only. For the runtime list use `GradeLevelAppropriatenessOutputSchema.shape.grade_band` |
| `Providers` (redundant alias; `Provider` already existed and is unchanged) | use `Provider` |

Removed outright, so a `TS2305` on any of these has an entry here:

| removed | replacement |
| --- | --- |
| `ComplexityClassification`, `ComplexityClassificationSchema` | each evaluator's own `<Evaluator>Result` / `<Evaluator>OutputSchema`, generated from its contract — all fifteen are exported, e.g. `PurposeClarityOutputSchema` |
| `PurposeComplexityLevel` | `PurposeClarityResult["complexity_score"]` |
| `VocabularyInternal`, `SmkInternal`, `ConventionalityInternal`, `PurposeInternal`, `SentenceStructureInternal`, `GradeLevelAppropriatenessInternal` | the matching `<Evaluator>Result` |

`TextComplexityEvaluator`, `evaluateTextComplexity`, `TextComplexityResult` and `TextComplexityLevel` are **removed with no replacement.** The composite ran several evaluators and merged their verdicts, which hid which model produced what. Call the evaluators you want and combine the results yourself, or use the `text-complexity` batch family, which does this with a report.

It ran four, whose 1.0 names are:

| composite key | 1.0 evaluator |
| --- | --- |
| `vocabulary` | `VocabularyComplexityEvaluator` |
| `sentenceStructure` | `SentenceStructureEvaluator` |
| `subjectMatterKnowledge` | `BackgroundKnowledgeDemandsEvaluator` |
| `conventionality` | `MeaningDirectnessEvaluator` |

**Mind the failure semantics.** The composite returned `{ error }` in place of any dimension
that failed and still gave you the rest. `Promise.all` does not — one failed dimension rejects
the whole call — so use `Promise.allSettled` if you want the old behaviour:

```typescript
const settled = await Promise.allSettled(
  DIMENSIONS.map(([, E]) => new E(keys).evaluate({ text, grade_level: grade })),
);

return settled.map((outcome, i) => {
  const [dimension, E] = DIMENSIONS[i];
  return {
    dimension,
    score:
      outcome.status === 'fulfilled'
        ? (readOutcome(outcome.value, E.metadata.outcome).score ?? null)
        : null,
  };
});
```

## 4. Errors are grouped by fault domain

`EvaluatorError` is still the root, but the middle of the hierarchy is new — you can now catch by who is at fault.

| 0.8.0 | 1.0.0 |
| --- | --- |
| `ValidationError` | `InputValidationError` |
| `TimeoutError` | `RequestTimeoutError` |
| `APIError` | **removed** — catch `DependencyError` instead |

`AuthenticationError`, `RateLimitError` and `NetworkError` kept their names but now extend `DependencyError` rather than `APIError`. `KnowledgeGraphError` also moved under `DependencyError`.

One reparenting is easy to miss: **`StandardNotFoundError` now extends `InputValidationError`**, not `KnowledgeGraphError`. A code that does not resolve is a bad input, not an upstream failure, so a `catch (e) { if (e instanceof KnowledgeGraphError) ... }` that used to see it no longer will.

New: `DependencyError`, `LLMProviderError`, `ConfigurationError` (thrown at construction for
a missing credential), and `LLMOutputProcessingError` for a response that arrived but could
not be used.

**The base class changed too**, which the rename table above does not cover:

| 0.8.0 | 1.0.0 |
| --- | --- |
| `EvaluatorError.code?: string` | **removed.** Use `instanceof`, or `error.constructor.name`; a `DependencyError` also carries `dependency` and `statusCode` |
| `new EvaluatorError(message, code?)` | `(message, retryable, cause?)` — and `EvaluatorError`, `EvaluationError` and `DependencyError` are now **abstract**, so a custom subclass or test fake needs updating |
| `APIError.statusCode?: number \| undefined` | `DependencyError.statusCode: number \| null` — `if (e.statusCode !== undefined)` now always passes |
| `retryable` on `APIError` | on every `EvaluatorError` |

**`EvaluationError` is the trap.** The name survives but means something entirely different:
0.8.0 exported it as a plain interface, `{ error: string; input: { text: string; grade?: string } }`,
which is what the removed composite handed you for a failed dimension. In 1.0 it is an abstract
error class. Code reading `.error` or `.input` off it fails with `TS2339`, and this hits exactly
the readers section 3 is written for.

## 5. `grade` is `gradeLevel` everywhere

The word "grade" meant three things across the API, the Knowledge Graph boundary and the batch CSV. It is now `gradeLevel` in camelCase contexts and `grade_level` in the wire and CSV formats.

- Evaluator input: `grade` → `grade_level`
- Batch and report fields: `grade` → `gradeLevel`
- **Result payloads are snake_case and always have been**, so no `gradeLevel` appears in one.
  Grade Level Appropriateness renamed its payload field `grade` → **`grade_band`** (see
  section 9); the complexity evaluators' verdict field is `complexity_score`
- Batch CSV column: `grade` → `grade_level` — **existing input files need the header renamed**:

  ```diff
  - text,grade
  + text,grade_level
  ```

  The other families' columns are in the [README](./README.md#batch).

## 6. The Learning Commons key is one option

```diff
- new MathStandardsAlignmentEvaluator({ platformApiKey: key });
- new SomeEvaluator({ partnerKey: key });
+ new MathStandardsAlignmentEvaluator({ learningCommonsApiKey: key });
```

Both `partnerKey` and `platformApiKey` are gone. `learningCommonsApiKey` on the evaluator config authorizes Learning Commons API calls such as the Knowledge Graph. Identified telemetry is a separate, opt-in setting: `telemetry: { learningCommonsApiKey: key }`.

**TypeScript will not always catch this.** Excess-property checking only applies to an object
literal written at the call site. If your keys come from a shared variable — the common case —
the removed property is silently ignored and identified telemetry just stops:

```typescript
const keys = { googleApiKey, partnerKey };   // no error; partnerKey is simply dropped
new VocabularyComplexityEvaluator(keys);
```

Grep for `partnerKey` and `platformApiKey` rather than relying on the compiler.

Math standards alignment is the exception that fails loudly: `learningCommonsApiKey` is a
required credential there, so dropping `platformApiKey` throws `ConfigurationError: Missing
required credential` at construction rather than degrading quietly.

## 7. Peer dependencies moved a major version

Covered by step 0 above, which has to happen first. For reference:

| Peer | 0.8.0 | 1.0.0 |
| --- | --- | --- |
| `ai` | `>=6.0.0` | `>=7.0.0 <8` |
| `@ai-sdk/google`, `@ai-sdk/openai`, `@ai-sdk/anthropic` | `>=3.0.0` | `>=4.0.0 <5` |
| `zod` | *(bundled as a dependency)* | `^4.1.8` — now a peer you declare |

The `zod` floor is `4.1.8` rather than `4.0.0` because `ai@7` itself requires
`zod@^3.25.76 || ^4.1.8`; a lower floor is not installable alongside it.

## 8. Math standards alignment: named inputs, and the envelope

Both the arguments and the return value changed. It was also the last evaluator returning its
payload bare.

```diff
- const alignment = await evaluator.evaluate(question, statementCode, jurisdiction);
- console.log(alignment.alignedCount);
+ const { result } = await evaluator.evaluate({
+   question,
+   statement_code: statementCode,
+   jurisdiction: Jurisdiction.MultiState, // an exported enum, not a string
+ });
+ console.log(result.aligned_count);
```

Every key is snake_case now, matching the other fifteen evaluators: `statement_code`,
`learning_components`, `aligned_count`, `total_count`. Nothing else about the payload changed.
Batch CSVs still accept `statementCode` as a column alias.

The evaluator needs **both** `anthropicApiKey` and `learningCommonsApiKey`;
`getEvaluator(id).requiredCredentials` lists the non-LLM ones.

`statement_code` is the bare dotted code, **not** the full CCSS URI: `"5.NF.A.1"`, not
`"CCSS.MATH.CONTENT.5.NF.A.1"`. The long form raises `StandardNotFoundError`. If you have
stored the long form, strip the prefix yourself — `normalizeStatementCode` looks like the fix
and is not, since it only trims and upper-cases:

```typescript
const bare = stored.replace(/^CCSS\.MATH\.CONTENT\./i, "");
```

`evaluateItems` keeps its name and arguments. **`evaluateByGrade` is now
`evaluateByGradeLevel`** — arguments unchanged. Neither returns an envelope: one call fans out
over many question × standard pairs, so there is no single model or duration to report.

## 9. Smaller behaviour changes

- **`supportedGrades`** — read as `SomeEvaluator.metadata.supportedGrades`, the static. It was
  never available on an instance in either version. It now reports what the contract says the
  evaluator targets. Previously it was derived from the grade input's enum, so the seven feedback evaluators and Grade Level Appropriateness published `[]`. It is not a validation set — where a `grade_level` input exists, its schema enum is what rejects a bad value.
- **Vocabulary Complexity** reports the model that actually ran for grades 3–4, which differs from the 5–12 branch. If you asserted one model string for all grades, it will now differ.
- **Grade Level Appropriateness and Sentence Structure** emit exactly the fields their contracts declare. GLA returns `grade_band`, `alternative_grade_band`, `scaffolding_needed`, `reasoning`.
- **The three complexity-score schemas** are generated from their contracts, so field descriptions and enum values follow the contract rather than a hand-written copy.

## What is new in 1.0.0

- **Seven feedback evaluators** judging teacher comments on student writing, each taking
  `{ student_text, feedback_text }` and returning a binary `quality_score`:
  `RevisionAccuracyEvaluator`, `RevisionActionabilityEvaluator`,
  `RevisionManageabilityEvaluator`, `StrengthAcknowledgmentEvaluator`,
  `StudentResponseSpecificityEvaluator`, `ToneAppropriatenessEvaluator`,
  `WithholdingAnswersEvaluator`. Also newly public:
  `OrganizationalStructureEvaluator`, `ReferenceKnowledgeDemandsEvaluator`, and
  `StandardNotFoundError` (see section 4 — it was not exported in 0.8.0).
- **`llmProvider`** — bring your own provider. Inject any `LLMProvider` and no API keys are needed, for Vertex AI, Bedrock, a gateway or an eval framework's model system. Mutually exclusive with `modelOverride`.
- **The `feedback` batch family**, alongside `text-complexity` and `math-standards-alignment`.
- **`getEvaluators()` / `getEvaluator(id)`** — a registry over all sixteen. Both return
  **metadata, not a constructor**: `{ id, stableId, idHistory, name, description, outcome,
  requiredCredentials, supportedGrades, defaultProviders }`. To run an evaluator, import it by
  name. 0.8.0's envelope carried no evaluator id — these are the ids it used internally, in
  telemetry and in batch reports — and every one of them still resolves:

  | id stored by 0.8.0 | resolves to |
  | --- | --- |
  | `vocabulary` | `student_facing_text.ela_reading.vocabulary_complexity` |
  | `sentence-structure` | `student_facing_text.ela_reading.sentence_structure` |
  | `subject-matter-knowledge` | `student_facing_text.ela_reading.background_knowledge_demands` |
  | `conventionality` | `student_facing_text.ela_reading.meaning_directness` |
  | `literacy.gla.purpose` | `student_facing_text.ela_reading.purpose_clarity` |
  | `grade-level-appropriateness` | `student_facing_text.ela_reading.grade_level_appropriateness` |
  | `math.standards-alignment` | `academic_standards_alignment.mathematics.math_standards_alignment` |

  `getEvaluator` returns `undefined` for anything it cannot resolve rather than throwing, so
  check before use. `text-complexity` returns `undefined` — that was the removed composite,
  not an evaluator. Each evaluator carries exactly one former id, so a class-name stem such as
  `smk` or `purpose` does not resolve; use the ids in the table.

The `@learning-commons/evaluators/batch` entry point and the `evaluators-batch` command both existed in 0.8.0; they are documented in the [README](./README.md) now, which is the change.
