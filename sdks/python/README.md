# learning-commons-evaluators

[![PyPI version](https://img.shields.io/pypi/v/learning-commons-evaluators)](https://pypi.org/project/learning-commons-evaluators/)

Python SDK for [Learning Commons evaluators](https://docs.learningcommons.org/evaluators/understanding-evaluators/introduction).

## Supported evaluators

| Evaluator family                                                                                                                                                                                                                       | Evaluator                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [**Text Complexity evaluators**](https://github.com/learning-commons-org/evaluators/tree/main/evals/text-complexity/) - [Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/introduction)                    | Grade Level Appropriateness<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/grade-level-appropriateness/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/grade-level-appropriateness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/grade-level-appropriateness)</li></ul>                  |
|                                                                                                                                                                                                                                        | Background Knowledge Demands<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/background-knowledge-demands/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/background-knowledge-demands/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/background-knowledge-demands)</li></ul>              |
|                                                                                                                                                                                                                                        | Vocabulary Complexity<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/vocabulary-complexity/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/vocabulary-complexity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/vocabulary-complexity)</li></ul>                                          |
|                                                                                                                                                                                                                                        | Sentence Structure<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/sentence-structure/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/sentence-structure/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/sentence-structure)</li></ul>                                                      |
|                                                                                                                                                                                                                                        | Meaning Directness<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/meaning-directness/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/meaning-directness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/meaning-directness)</li></ul>                                                      |
|                                                                                                                                                                                                                                        | Purpose Clarity<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/purpose-clarity/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/purpose-clarity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/purpose-clarity)</li></ul>                                                                  |
|                                                                                                                                                                                                                                        | Organizational Structure<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/organizational-structure/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/organizational-structure/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/organizational-structure)</li></ul>                              |
|                                                                                                                                                                                                                                        | Reference Knowledge Demands<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/reference-knowledge-demands/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/text-complexity/ela-reading/reference-knowledge-demands/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/text-complexity-evaluators/reference-knowledge-demands)</li></ul>                  |
| [**Graphics evaluators**](https://github.com/learning-commons-org/evaluators/tree/main/evals/graphics/) - [Docs](https://docs.learningcommons.org/evaluators/graphics-evaluators/introduction)                                         | Graphics Complexity<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/graphics/ela/graphics-complexity/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/graphics/ela/graphics-complexity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/graphics-evaluators/graphics-complexity)</li></ul>                                                                                       |
|                                                                                                                                                                                                                                        | Graphics Accuracy<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/graphics/math/graphics-accuracy/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/graphics/math/graphics-accuracy/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/graphics-evaluators/graphics-accuracy)</li></ul>                                                                                             |
| [**Feedback evaluators**](https://github.com/learning-commons-org/evaluators/tree/main/evals/feedback/) - [Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/introduction)                                         | Strength Acknowledgment<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/strength-acknowledgment/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/strength-acknowledgment/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/strength-acknowledgment)</li></ul>                                                       |
|                                                                                                                                                                                                                                        | Revision Actionability<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-actionability/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-actionability/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-actionability)</li></ul>                                                           |
|                                                                                                                                                                                                                                        | Student Response Specificity<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/student-response-specificity/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/student-response-specificity/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/student-response-specificity)</li></ul>                                   |
|                                                                                                                                                                                                                                        | Revision Accuracy<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-accuracy/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-accuracy/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-accuracy)</li></ul>                                                                               |
|                                                                                                                                                                                                                                        | Revision Manageability<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-manageability/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/revision-manageability/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/revision-manageability)</li></ul>                                                           |
|                                                                                                                                                                                                                                        | Withholding Answers<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/withholding-answers/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/withholding-answers/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/withholding-answers)</li></ul>                                                                       |
|                                                                                                                                                                                                                                        | Tone Appropriateness<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/tone-appropriateness/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/feedback/ela-writing/tone-appropriateness/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/feedback-evaluators/tone-appropriateness)</li></ul>                                                                   |
| [**Academic Standards evaluators**](https://github.com/learning-commons-org/evaluators/tree/main/evals/academic-standards-alignment/) - [Docs](https://docs.learningcommons.org/evaluators/academic-standards-evaluators/introduction) | Math Standards Alignment<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/academic-standards-alignment/mathematics/math-standards-alignment/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/academic-standards-alignment/mathematics/math-standards-alignment/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/academic-standards-evaluators/math-standards-alignment)</li></ul> |
| [**Durable Skills evaluators**](https://github.com/learning-commons-org/evaluators/tree/main/evals/durable-skills/) - [Docs](https://docs.learningcommons.org/evaluators/durable-skills-evaluators/introduction)                       | Critical Thinking<ul><li>[Input schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/durable-skills/ela-writing/critical-thinking/input_schema.json)</li><li>[Output schema](https://github.com/learning-commons-org/evaluators/blob/main/evals/durable-skills/ela-writing/critical-thinking/output_schema.json)</li><li>[Docs](https://docs.learningcommons.org/evaluators/durable-skills-evaluators/critical-thinking)</li></ul>                                                             |

## Dependencies

- Python 3.11+
- The provider clients ship with the package (`openai`, `anthropic`, `google-genai`), along with `pydantic`, `httpx`, `pillow`, and `textstat`.
- Credentials are constructor arguments. The SDK reads no provider keys from the environment, so a shell `GOOGLE_API_KEY` leaves `google_api_key` unset. A missing key raises `ConfigurationError` at construction, before any I/O.

## Installation

Install the SDK:

```bash
pip install learning-commons-evaluators
```

Pass the key each evaluator's default provider requires ([which keys](https://docs.learningcommons.org/evaluators/getting-started/quickstart#required-api-keys)):

```python
GradeLevelAppropriatenessEvaluator(google_api_key="...")       # Google
SentenceStructureEvaluator(openai_api_key="...")                # OpenAI
CriticalThinkingEvaluator(anthropic_api_key="...")              # Anthropic
VocabularyComplexityEvaluator(openai_api_key="...", google_api_key="...")
MathStandardsAlignmentEvaluator(
    anthropic_api_key="...",
    learning_commons_api_key="...",  # Knowledge Graph
)
```

## Quickstart

```python
from learning_commons_evaluators import GradeLevelAppropriatenessEvaluator

# Configure evaluator
evaluator = GradeLevelAppropriatenessEvaluator(google_api_key="...")

# Run an evaluation
evaluation = evaluator.evaluate_sync(text="The cat's out of the bag now.")

# Print evaluation results
print(evaluation.result.grade_band)              # a CCSS band, e.g. "2-3"
print(evaluation.result.alternative_grade_band)  # the band reachable with scaffolding
print(evaluation.result.scaffolding_needed)      # what that band would need
print(evaluation.metadata.model)                 # "google:gemini-3.6-flash"
```

`await evaluator.evaluate(...)` is the same call from async code. `evaluate_sync` runs it to completion with `asyncio.run`, so call it from synchronous code. Inside a running event loop, await `evaluate`.

## Methods

The package provides the following:

- [Discovery](#discovery)
- [Evaluation](#evaluation)
- [Outcomes](#outcomes)
- [Standards](#standards)
- [Text features](#text-features)

Import them from `learning_commons_evaluators`. The text-feature helpers live in `learning_commons_evaluators.features`.

### Discovery

```python
from learning_commons_evaluators import get_evaluators, get_evaluator

get_evaluators()
# tuple[EvaluatorMetadata, ...] — every evaluator, in taxonomy order

get_evaluator("text_complexity.ela_reading.vocabulary_complexity")
# EvaluatorMetadata | None — current and historical ids both resolve

get_evaluator("grade-level-appropriateness").id
# "text_complexity.ela_reading.grade_level_appropriateness"
```

`EvaluatorMetadata` carries `id`, `stable_id`, `id_history`, `name`, `description`, `supported_grades`, `default_providers`, `required_credentials`, and an `outcome` block naming which result fields hold the verdict and its rationale (`None` when the evaluator declares no single verdict). `required_credentials` lists only non-LLM services: `("learning_commons_api_key",)` for math standards alignment and `()` for the other eighteen. Provider keys follow `default_providers`, so `(Provider.GOOGLE,)` means supply `google_api_key`.

### Evaluation

Every evaluator class exposes `.evaluate(...)` and `.evaluate_sync(...)` (see [Supported evaluators](#supported-evaluators) for each evaluator's input and output).

Pass the contract's fields as keywords, or pass the evaluator's input model. Passing both raises `TypeError`.

```python
from learning_commons_evaluators import (
    GradeLevelAppropriatenessEvaluator,
    GradeLevelAppropriatenessInput,
)

evaluator = GradeLevelAppropriatenessEvaluator(google_api_key="...")

# Keywords
await evaluator.evaluate(text="The cat's out of the bag now.")

# The same call, synchronous, with the input model
evaluator.evaluate_sync(
    GradeLevelAppropriatenessInput(text="The cat's out of the bag now.")
)
```

| Evaluator family   | Evaluator                             | Typical input                                        |
| ------------------ | ------------------------------------- | ---------------------------------------------------- |
| Text Complexity    | `GradeLevelAppropriatenessEvaluator`  | `{ text }`                                           |
|                    | `BackgroundKnowledgeDemandsEvaluator` | `{ text, grade_level }`                              |
|                    | `VocabularyComplexityEvaluator`       | `{ text, grade_level }`                              |
|                    | `SentenceStructureEvaluator`          | `{ text, grade_level }`                              |
|                    | `MeaningDirectnessEvaluator`          | `{ text, grade_level }`                              |
|                    | `PurposeClarityEvaluator`             | `{ text, grade_level }`                              |
|                    | `OrganizationalStructureEvaluator`    | `{ text, grade_level }`                              |
|                    | `ReferenceKnowledgeDemandsEvaluator`  | `{ text, grade_level }`                              |
| Graphics           | `GraphicsComplexityEvaluator`         | `{ text, grade_level, image_paths, figure_labels? }` |
|                    | `GraphicsAccuracyEvaluator`           | `{ image_paths, claim }`                             |
| Feedback           | `StrengthAcknowledgmentEvaluator`     | `{ student_text, feedback_text }`                    |
|                    | `RevisionActionabilityEvaluator`      | `{ student_text, feedback_text }`                    |
|                    | `StudentResponseSpecificityEvaluator` | `{ student_text, feedback_text }`                    |
|                    | `RevisionAccuracyEvaluator`           | `{ student_text, feedback_text }`                    |
|                    | `RevisionManageabilityEvaluator`      | `{ student_text, feedback_text }`                    |
|                    | `WithholdingAnswersEvaluator`         | `{ student_text, feedback_text }`                    |
|                    | `ToneAppropriatenessEvaluator`        | `{ student_text, feedback_text }`                    |
| Academic Standards | `MathStandardsAlignmentEvaluator`     | `{ question, case_identifier_uuid }`                 |
| Durable Skills     | `CriticalThinkingEvaluator`           | `{ assignment_text, source_passages, essay_text }`   |

Every call returns an `EvaluationResult`: `evaluator` (the registry id), `result` (that evaluator's output model, keys unchanged), and `metadata` (`model`, `processing_time_ms`, `token_usage`). `metadata.model` is `"provider:model"`, joined with `+` when several models ran. An evaluator whose contract declares several steps sums token usage across them.

`grade_level` on the text-complexity and graphics-complexity evaluators is an `int` (`3`–`12`). Vocabulary Complexity takes a different model branch for grades 3–4 than for 5–12, and construction validates the union of keys those branches need, so it requires both `openai_api_key` and `google_api_key` at every grade.

Each graphics path is a local file, read in your process. The SDK checks format, size, and edge limits before any model call. A file outside those limits raises `InputValidationError`. For a question with its expected answer, build the claim with `compose_graphics_accuracy_claim(question, answer)`, which produces the text the evaluator was measured with:

```python
from learning_commons_evaluators import (
    GraphicsAccuracyEvaluator,
    compose_graphics_accuracy_claim,
)

evaluation = GraphicsAccuracyEvaluator(google_api_key="...").evaluate_sync(
    image_paths=["figures/apples-in-baskets.png"],
    claim=compose_graphics_accuracy_claim("How many apples are there altogether?", "12"),
)
print(evaluation.result.is_correct, evaluation.result.basis)
```

`source_passages` is a list of `{title?, author?, text}` in the order the student received them. The first item is Source 1. A passage may omit `title` and `author`.

The Math Standards Alignment evaluator also exposes `.evaluate_by_code()`. `evaluate` / `evaluate_sync` take the CASE Network UUID. `evaluate_by_code` is async: it resolves a statement code, then runs the same evaluation.

```python
import asyncio

from learning_commons_evaluators import Jurisdiction, MathStandardsAlignmentEvaluator

math = MathStandardsAlignmentEvaluator(
    anthropic_api_key="...",
    learning_commons_api_key="...",
)

# UUID: evaluate_sync wraps evaluate()
math.evaluate_sync(
    question="…",
    case_identifier_uuid="6ba25656-d7cc-11e8-824f-0242ac160002",
)

# Statement code, as that jurisdiction spells it
asyncio.run(
    math.evaluate_by_code(
        question="…",
        statement_code="3.MD.C.7.d",
        jurisdiction=Jurisdiction.MULTI_STATE,  # optional; Multi-State is Common Core
        grade_level="3",                        # optional; see below
    )
)
```

Spell the code the way its jurisdiction spells it. A code is a lookup key: Ohio writes `3.MD.7` where Common Core writes `3.MD.C.7`. A Common Core code with `jurisdiction=Jurisdiction.OHIO` raises `StandardNotFoundError`. `grade_level` (`"K"` through `"12"`) is consulted only when one code matches several standards. With no grade, the first copy that has learning components is evaluated. A grade that matches no copy raises `InputValidationError`. `result.statement_code` is the Knowledge Graph's own spelling of the copy that was judged, and `result.case_identifier_uuid` names it. The contract declares no single score, so `read_outcome(...).score` is `None`.

### Outcomes

```python
from learning_commons_evaluators import get_evaluator, read_outcome

evaluation = evaluator.evaluate_sync(text="The cat's out of the bag now.")
declared = get_evaluator(evaluation.evaluator)
outcome = read_outcome(evaluation, declared.outcome if declared else None)
print(outcome.score)       # the verdict, as one comparable string
print(outcome.reasoning)
```

`read_outcome` picks the verdict and rationale named by the evaluator's declared `outcome` block.

`score` is a string when the field is present. A boolean verdict is `"true"` or `"false"` (Graphics Accuracy). A feedback `quality_score` of `0` or `1` is `"0"` or `"1"`. `"0"` is truthy, so compare explicitly (`score == "1"`), or read the numeric field from `evaluation.result` directly. `score` is `None` when the evaluator has no declared outcome or the payload is missing that field — a reporting gap. Math Standards Alignment is that case.

### Standards

```python
from learning_commons_evaluators import (
    Jurisdiction,
    KnowledgeGraphClient,
    normalize_statement_code,
)

normalize_statement_code("  5.nbt.a.1 ")  # "5.NBT.A.1"

async with KnowledgeGraphClient(api_key) as kg:
    matches = await kg.search_standards("5.NBT.A.1", jurisdiction=Jurisdiction.MULTI_STATE)
    standard = await kg.get_academic_standard(matches[0].case_identifier_uuid)
    components = await kg.get_learning_components(matches[0].case_identifier_uuid)
    component_set = await kg.get_learning_component_set(matches[0].case_identifier_uuid)
```

| Method                                             | Returns                                                                      | Raises                                                                  |
| -------------------------------------------------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| `search_standards(statement_code, ...)`            | every match, best first (`StandardMatch`)                                    | `InputValidationError`, `StandardNotFoundError`, Knowledge Graph errors |
| `get_academic_standard(case_identifier_uuid)`      | one `AcademicStandard`                                                       | `InputValidationError`, Knowledge Graph errors                          |
| `get_learning_components(case_identifier_uuid)`    | evaluable `LearningComponent`s (descriptions present)                        | `InputValidationError`, `KnowledgeGraphError`                           |
| `get_learning_component_set(case_identifier_uuid)` | those components plus `undescribed_count` for components with no description | `InputValidationError`, `KnowledgeGraphError`                           |

`search_standards` defaults to `Jurisdiction.MULTI_STATE` (Common Core). Pass `jurisdiction` or `academic_subject` to override that. More than one match means the code is reused across courses or frameworks.

The client owns an HTTP connection pool, so close it (`async with`, or `await kg.aclose()`). It is bound to the event loop that first uses it. Keep one client inside one `asyncio.run`. Evaluators open and close the clients they need for each evaluation, so one evaluator can be reused across `evaluate_sync` calls.

### Text features

These power sentence-structure preprocessing. They are deterministic and do not call a model. Counts come from `textstat`, which is the library the sentence-structure contract binds for Python.

```python
from learning_commons_evaluators.features import (
    add_engineered_features,
    features_to_json,
    readability_counts,
)

readability_counts(text)          # ReadabilityCounts: counts and flesch_kincaid_grade
add_engineered_features(analysis)  # sentence analysis → features
features_to_json(features)         # JSON string for a prompt
```

## More resources

[Check out the docs](https://docs.learningcommons.org/evaluators/sdk-api-reference/overview) for more implementation details:

- [Configuration](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/configuration), including model overrides, logging, and telemetry
- [Inputs and output schemas](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/evaluation) for all [Supported evaluators](#supported-evaluators)
  - Read a feedback evaluator's criterion keys with `list(ToneAppropriatenessOutput.model_fields["key_features"].annotation.model_fields)`
- [Error handling](https://docs.learningcommons.org/evaluators/sdk-api-reference/python/error-handling) — the same hierarchy is written up in [docs/error-handling.md](https://github.com/learning-commons-org/evaluators/blob/main/sdks/python/docs/error-handling.md)
- [Local development](https://github.com/learning-commons-org/evaluators/blob/main/sdks/python/docs/local-development.md)

## License

MIT
