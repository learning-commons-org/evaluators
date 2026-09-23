# @learning-commons/evaluators

[![npm version](https://img.shields.io/npm/v/@learning-commons/evaluators)](https://www.npmjs.com/package/@learning-commons/evaluators)

TypeScript SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction).

## Supported evaluators

| Evaluator family                                                                                                                                                                         | Evaluator                                                                                                                                                                                                                                                                                                                                                                                              |
| :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| <ul><li>[Text Complexity](../../evals/text-complexity/)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/introduction)</li></ul>                    | Grade Level Appropriateness<ul><li>[Input schema](../../evals/text-complexity/ela-reading/grade-level-appropriateness/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/grade-level-appropriateness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/grade-level-appropriateness)</li></ul>                  |
|                                                                                                                                                                                          | Background Knowledge Demands<ul><li>[Input schema](../../evals/text-complexity/ela-reading/background-knowledge-demands/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/background-knowledge-demands/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/background-knowledge-demands)</li></ul>              |
|                                                                                                                                                                                          | Vocabulary Complexity<ul><li>[Input schema](../../evals/text-complexity/ela-reading/vocabulary-complexity/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/vocabulary-complexity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/vocabulary-complexity)</li></ul>                                          |
|                                                                                                                                                                                          | Sentence Structure<ul><li>[Input schema](../../evals/text-complexity/ela-reading/sentence-structure/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/sentence-structure/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/sentence-structure)</li></ul>                                                      |
|                                                                                                                                                                                          | Meaning Directness<ul><li>[Input schema](../../evals/text-complexity/ela-reading/meaning-directness/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/meaning-directness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/meaning-directness)</li></ul>                                                      |
|                                                                                                                                                                                          | Purpose Clarity<ul><li>[Input schema](../../evals/text-complexity/ela-reading/purpose-clarity/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/purpose-clarity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/purpose-clarity)</li></ul>                                                                  |
|                                                                                                                                                                                          | Organizational Structure<ul><li>[Input schema](../../evals/text-complexity/ela-reading/organizational-structure/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/organizational-structure/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/organizational-structure)</li></ul>                              |
|                                                                                                                                                                                          | Reference Knowledge Demands<ul><li>[Input schema](../../evals/text-complexity/ela-reading/reference-knowledge-demands/input_schema.json)</li><li>[Output schema](../../evals/text-complexity/ela-reading/reference-knowledge-demands/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/reference-knowledge-demands)</li></ul>                  |
| <ul><li>[Feedback](../../evals/feedback/)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/introduction)</li></ul>                                         | Strength Acknowledgment<ul><li>[Input schema](../../evals/feedback/ela-writing/strength-acknowledgment/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/strength-acknowledgment/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/strength-acknowledgment)</li></ul>                                                       |
|                                                                                                                                                                                          | Revision Actionability<ul><li>[Input schema](../../evals/feedback/ela-writing/revision-actionability/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/revision-actionability/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-actionability)</li></ul>                                                           |
|                                                                                                                                                                                          | Student Response Specificity<ul><li>[Input schema](../../evals/feedback/ela-writing/student-response-specificity/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/student-response-specificity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/student-response-specificity)</li></ul>                                   |
|                                                                                                                                                                                          | Revision Accuracy<ul><li>[Input schema](../../evals/feedback/ela-writing/revision-accuracy/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/revision-accuracy/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-accuracy)</li></ul>                                                                               |
|                                                                                                                                                                                          | Revision Manageability<ul><li>[Input schema](../../evals/feedback/ela-writing/revision-manageability/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/revision-manageability/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-manageability)</li></ul>                                                           |
|                                                                                                                                                                                          | Withholding Answers<ul><li>[Input schema](../../evals/feedback/ela-writing/withholding-answers/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/withholding-answers/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/withholding-answers)</li></ul>                                                                       |
|                                                                                                                                                                                          | Tone Appropriateness<ul><li>[Input schema](../../evals/feedback/ela-writing/tone-appropriateness/input_schema.json)</li><li>[Output schema](../../evals/feedback/ela-writing/tone-appropriateness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/tone-appropriateness)</li></ul>                                                                   |
| <ul><li>[Academic Standards](../../evals/academic-standards-alignment/)</li><li>[Docs](https://docs.learningcommons.org/evaluators/academic-standards-evaluators/introduction)</li></ul> | Math Standards Alignment<ul><li>[Input schema](../../evals/academic-standards-alignment/mathematics/math-standards-alignment/input_schema.json)</li><li>[Output schema](../../evals/academic-standards-alignment/mathematics/math-standards-alignment/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/academic-standards-evaluators/math-standards-alignment)</li></ul> |

## Dependencies

- Node 20.19+ or 22.12+ (`^20.19.0 || >=22.12.0`)
- Type packages:

  ```bash
  npm install -D typescript @types/node @types/json-schema
  ```

- [Vercel AI](https://sdk.vercel.ai) and [`zod`](https://zod.dev) version 4:

  ```bash
  npm install ai zod@^4.1.8
  ```

- In your project's `package.json`:

  ```json
  {
    "type": "module",
    "compilerOptions": {
      "module": "nodenext",
      "moduleResolution": "nodenext",
      "target": "es2022",
      "strict": true,
      "types": ["node"]
    }
  }
  ```

## Installation

> See [MIGRATION.md](./MIGRATION.md) if upgrading from an earlier major version.

Install the SDK:

```bash
npm install @learning-commons/evaluators
```

And the provider adapter(s) for the evaluators you plan to run (See [Required API keys](https://docs.learningcommons.org/evaluators/getting-started/quickstart#required-api-keys) for each evaluator):

```bash
npm install @ai-sdk/openai     # OpenAI
npm install @ai-sdk/google     # Google Gemini
npm install @ai-sdk/anthropic  # Anthropic
```

## Quickstart

```typescript
import { GradeLevelAppropriatenessEvaluator } from "@learning-commons/evaluators";

// Configure evaluator
const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});

// Run an evaluation
const { result, metadata } = await evaluator.evaluate({
  text: "The cat's out of the bag now.",
});

// Print evaluation results
console.log(result.grade_band); // a CCSS band, e.g. "2-3"
console.log(result.alternative_grade_band); // the band reachable with scaffolding
console.log(result.scaffolding_needed); // what that band would need
console.log(metadata.model); // "google:gemini-3.6-flash"
```

## Methods

The package provides methods to import across the following categories:

- [Discovery](#discovery)
- [Evaluation](#evaluation)
- [Outcomes](#outcomes)
- [Standards](#standards)
- [Text features](#text-features)
- [Batch evaluation](#batch-evaluation)

These methods can be imported via 2 entry points:

- `@learning-commons/evaluators` - Standalone functions and the evaluator classes
- `@learning-commons/evaluators/batch` - Batch evaluation

### Discovery

```typescript
import { getEvaluators, getEvaluator } from "@learning-commons/evaluators";

getEvaluators();
// readonly EvaluatorMetadata[] — every evaluator, in taxonomy order

getEvaluator("text_complexity.ela_reading.vocabulary_complexity");
// EvaluatorMetadata | undefined — current and historical ids both resolve
```

`EvaluatorMetadata` carries `id`, `stableId`, `idHistory`, `name`,
`description`, `supportedGrades`, `defaultProviders`, optional
`requiredCredentials`, and an optional `outcome` block naming which result
fields hold the verdict and its rationale.

### Evaluation

Every evaluator class exposes `evaluate(input)` (see [Supported evaluators](#supported-evaluators) for each evaluator's input and output).

Each evaluator class also has a matching helper `evaluate<Name>(input, config)`:

| Evaluator                             | Helper                               | Typical input                                |
| ------------------------------------- | ------------------------------------ | -------------------------------------------- |
| `GradeLevelAppropriatenessEvaluator`  | `evaluateGradeLevelAppropriateness`  | `{ text }`                                   |
| `BackgroundKnowledgeDemandsEvaluator` | `evaluateBackgroundKnowledgeDemands` | `{ text, grade_level }`                      |
| `VocabularyComplexityEvaluator`       | `evaluateVocabularyComplexity`       | `{ text, grade_level }`                      |
| `SentenceStructureEvaluator`          | `evaluateSentenceStructure`          | `{ text, grade_level }`                      |
| `MeaningDirectnessEvaluator`          | `evaluateMeaningDirectness`          | `{ text, grade_level }`                      |
| `PurposeClarityEvaluator`             | `evaluatePurposeClarity`             | `{ text, grade_level }`                      |
| `OrganizationalStructureEvaluator`    | `evaluateOrganizationalStructure`    | `{ text, grade_level }`                      |
| `ReferenceKnowledgeDemandsEvaluator`  | `evaluateReferenceKnowledgeDemands`  | `{ text, grade_level }`                      |
| `StrengthAcknowledgmentEvaluator`     | `evaluateStrengthAcknowledgment`     | `{ student_text, feedback_text }`            |
| `RevisionActionabilityEvaluator`      | `evaluateRevisionActionability`      | `{ student_text, feedback_text }`            |
| `StudentResponseSpecificityEvaluator` | `evaluateStudentResponseSpecificity` | `{ student_text, feedback_text }`            |
| `RevisionAccuracyEvaluator`           | `evaluateRevisionAccuracy`           | `{ student_text, feedback_text }`            |
| `RevisionManageabilityEvaluator`      | `evaluateRevisionManageability`      | `{ student_text, feedback_text }`            |
| `WithholdingAnswersEvaluator`         | `evaluateWithholdingAnswers`         | `{ student_text, feedback_text }`            |
| `ToneAppropriatenessEvaluator`        | `evaluateToneAppropriateness`        | `{ student_text, feedback_text }`            |
| `MathStandardsAlignmentEvaluator`     | `evaluateMathStandardsAlignment`     | `{ question, statement_code, jurisdiction }` |

```typescript example.ts
import {
  GradeLevelAppropriatenessEvaluator,
  evaluateGradeLevelAppropriateness,
} from "@learning-commons/evaluators";

// Option 1
const evaluator = new GradeLevelAppropriatenessEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
});
await evaluator.evaluate({ text: "The cat's out of the bag now." });

// Option 2: Equivalent helper function: configures, evaluates, discards the instance
await evaluateGradeLevelAppropriateness(
  { text: "The cat's out of the bag now." },
  { googleApiKey: process.env.GOOGLE_API_KEY },
);
```

`MathStandardsAlignmentEvaluator` adds 2 bulk methods on the instance - `evaluateItems` and `evaluateByGradeLevel` (these have no helpers):

```typescript
import {
  MathStandardsAlignmentEvaluator,
  Jurisdiction,
} from "@learning-commons/evaluators";

const math = new MathStandardsAlignmentEvaluator({
  anthropicApiKey: process.env.ANTHROPIC_API_KEY,
  learningCommonsApiKey: process.env.LEARNING_COMMONS_API_KEY,
});

// M questions × per-question statement codes
await math.evaluateItems(
  [{ question: "…", statement_codes: ["5.NBT.A.1"] }],
  Jurisdiction.MultiState,
  { useCoarseFilter: true, onProgress: (done, total) => {} },
);

// Fetch every math standard for a grade, then evaluate each question against them
await math.evaluateByGradeLevel(["…"], "5", Jurisdiction.MultiState);
```

### Outcomes

```typescript
import { getEvaluator, readOutcome } from "@learning-commons/evaluators";

const evaluation = await evaluator.evaluate(input);
const outcome = getEvaluator(evaluation.evaluator)?.outcome;
const { score, reasoning } = readOutcome(evaluation, outcome);
```

`readOutcome` picks the verdict and rationale named by the evaluator's declared `outcome` block. `score` is `undefined` when the evaluator has no declared outcome or the payload is missing that field — a reporting gap, not an evaluation failure.

### Standards

```typescript
import {
  Jurisdiction,
  StandardsCatalog,
  normalizeStatementCode,
} from "@learning-commons/evaluators";

normalizeStatementCode("  5.nbt.a.1 "); // "5.NBT.A.1"

const catalog = new StandardsCatalog({
  learningCommonsApiKey: process.env.LEARNING_COMMONS_API_KEY,
  academicSubject: "Mathematics",
});

await catalog.listStandards("5", { jurisdiction: Jurisdiction.MultiState });
await catalog.getStandard("5.NBT.A.1");
await catalog.resolveStandard("5.NBT.A.1");
await catalog.validateCodes(["5.NBT.A.1", "5.NBT.A.2"]);
```

| Method                                  | Returns                                                                                             | Throws                                            |
| --------------------------------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `listStandards(gradeLevel, opts?)`      | every instructional standard for that grade                                                         | Knowledge Graph / auth errors                     |
| `getStandard(statementCode, opts?)`     | one `StandardInfo`                                                                                  | `InputValidationError`, `StandardNotFoundError`   |
| `resolveStandard(statementCode, opts?)` | a `CodeValidation` (`resolved`, `ambiguous`, `not-found`, `no-learning-components`, or `unchecked`) | only `AuthenticationError` / `ConfigurationError` |
| `validateCodes(statementCodes, opts?)`  | one `CodeValidation` per distinct normalized code                                                   | only `AuthenticationError` / `ConfigurationError` |

Lookups default to Multi-State (Common Core). Pass `jurisdiction` or `academicSubject` on the call to override the catalog defaults.

### Text features

These power sentence-structure preprocessing. They are deterministic and do not call a model.

```typescript
import {
  calculateFleschKincaidGrade,
  calculateReadabilityMetrics,
  addEngineeredFeatures,
  featuresToJSON,
} from "@learning-commons/evaluators";

calculateFleschKincaidGrade(text); // number
calculateReadabilityMetrics(text); // counts, averages, and the FK grade
addEngineeredFeatures(analysis); // SentenceAnalysis → SentenceFeatures
featuresToJSON(features); // JSON string for a prompt
```

### Batch evaluation

```typescript
import {
  BatchEvaluator,
  getFamilies,
  getFamily,
  parseCSV,
  renderOutputs,
  formatAsCSV,
  formatAsJSON,
  formatAsHTML,
} from "@learning-commons/evaluators/batch";

getFamilies(); // [text-complexity, math-standards-alignment, feedback]
getFamily("feedback"); // throws if the id is unknown

const rows = parseCSV("./texts.csv"); // a path, not CSV text
const batch = new BatchEvaluator({
  googleApiKey: process.env.GOOGLE_API_KEY,
  openaiApiKey: process.env.OPENAI_API_KEY,
});

const output = await batch.evaluate(rows, "text-complexity", {
  selectedMemberIds: ["text_complexity.ela_reading.vocabulary_complexity"],
  onProgress: (result) => {},
});

batch.cancel(); // stops in-flight work; returns results collected so far

const { csv, json, html } = renderOutputs("text-complexity", output, {
  csvPath: "./texts.csv",
  groupId: "text-complexity",
  reportId: "run-1",
  generatedAt: new Date(),
  totalInputRows: rows.length,
});
```

| Function                                            | Role                                                                                       |
| --------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| `getFamilies()`                                     | every family, copied so callers cannot mutate the registry                                 |
| `getFamily(id)`                                     | one family (`members`, `columns`, `maxInputRows`); throws listing valid ids                |
| `parseCSV(path)`                                    | file → `BatchInput[]`; family column rules apply later                                     |
| `BatchEvaluator.evaluate(inputs, family, options?)` | run the family (or a subset) over the rows                                                 |
| `BatchEvaluator.cancel()`                           | abort and return partial `BatchResult[]`                                                   |
| `renderOutputs(familyId, output, meta)`             | the same CSV / JSON / HTML the CLI writes (`html` is absent when the family has no report) |
| `formatAsCSV(output)`                               | flattened per-row summary                                                                  |
| `formatAsJSON(output, meta)`                        | machine-readable per-(row, evaluator) records                                              |
| `formatAsHTML(output, meta)`                        | text-complexity rubric report                                                              |

`evaluate` accepts a family id or an `EvaluatorFamily` object. For the CLI,
column requirements, and report shapes, see [`src/batch/README.md`](./src/batch/README.md).

## More resources

[Check out the docs](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview) for more implementation details:

- [Configuration](https://docs.learningcommons.org/evaluators/sdk-api-reference/typescript/configuration), including model overrides
- Input and [output](https://docs.learningcommons.org/evaluators/sdk-api-reference/typescript/outputs) schemas for all [Supported evaluators](#supported-evaluators)
  - Read exported schemas with `Object.keys(ToneAppropriatenessOutputSchema.shape.key_features.shape)`
- [Error handling](https://docs.learningcommons.org/evaluators/sdk-api-reference/typescript/error-handling)
- [Batch evaluator](https://docs.learningcommons.org/evaluators/sdk-api-reference/typescript/batch-evaluator)

## License

MIT
