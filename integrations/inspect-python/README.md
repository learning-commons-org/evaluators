# learning-commons-inspect-scorers

[Inspect AI](https://inspect.aisi.org.uk/) scorer wrappers for the [Learning Commons evaluators](https://github.com/learning-commons-org/evaluators) SDK.

## Installation

```bash
pip install learning-commons-inspect-scorers
```

> **Note:** Requires `learning-commons-evaluators>=0.2.0`. During local development
> install the SDK from the repo root first:
> ```bash
> pip install -e sdks/python
> pip install -e integrations/inspect-python
> ```

## Usage

### Grade Level Appropriateness scorer

Evaluates whether model output (or generated artifact files) is written at the
appropriate reading level for a target K-12 grade band.

```python
from inspect_ai import Task, task
from inspect_ai.dataset import csv_dataset, FieldSpec
from inspect_ai.solver import generate
from learning_commons_inspect_scorers import gla_scorer

@task
def my_eval():
    return Task(
        dataset=csv_dataset("samples.csv"),  # requires target_grade column
        solver=[generate()],
        scorer=gla_scorer(),
    )
```

The dataset CSV must include a `target_grade` metadata column with one of:
`K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-CCR`.

### Scoring text your task produced (not the completion)

By default the scorer grades `state.output.completion`. To grade text from
somewhere else — files your solver wrote, a specific message, filtered content —
pass a `text_fn`. This keeps task-specific knowledge (file layout, naming,
formatting) in your task, not in this package:

```python
def student_artifact_text(state):
    # read whatever your task produced; return None to skip the sample
    return "\n\n".join(read_my_files(state)) or None

scorer=gla_scorer(text_fn=student_artifact_text)
```

### Re-scoring an existing log from the CLI

Once installed, scorers are registered via Inspect's entry point system:

```bash
inspect score logs/my-eval.eval --scorer learning_commons_inspect_scorers/gla_scorer
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `grader_model` | `"anthropic/claude-opus-4-8"` | Inspect model string for the grading LLM. Uses Inspect's model system — no separate API key configuration needed. |
| `target_grade_key` | `"target_grade"` | Metadata key holding the expected grade band. |
| `allow_adjacent` | `True` | If `True`, the one grade band above or below the target also passes. |
| `text_fn` | `None` | Callable `(TaskState) -> str \| None` returning the text to grade. Defaults to `state.output.completion`. Return `None`/empty to skip the sample. Caller keeps text within the evaluator's input-length limit. |

## Development

```bash
# From repo root
pip install -e sdks/python
pip install -e "integrations/inspect-python[dev]"
pytest integrations/inspect-python/tests/
```
