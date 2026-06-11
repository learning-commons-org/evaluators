# learning-commons-inspect-scorers

[Inspect AI](https://inspect.aisi.org.uk/) scorer wrappers for the [Learning Commons evaluators](https://github.com/learning-commons-org/evaluators) SDK.

## Installation

```bash
pip install learning-commons-inspect-scorers
```

> **Note:** Requires `learning-commons-evaluators>=0.2.0`. During local development
> (before 0.2.0 is published), install the SDK from the repo root first:
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
from learning_commons_evaluators.config import create_config_no_telemetry
from learning_commons_evaluators.schemas.config import GoogleLLMProviderConfig

config = create_config_no_telemetry(
    google_llm_provider_config=GoogleLLMProviderConfig(api_key="your-key"),
)

@task
def my_eval():
    return Task(
        dataset=csv_dataset("samples.csv"),  # requires target_grade column
        solver=[generate()],
        scorer=gla_scorer(config=config),
    )
```

The dataset CSV must include a `target_grade` metadata column with one of:
`K-1`, `2-3`, `4-5`, `6-8`, `9-10`, `11-CCR`.

### Scoring artifact files (edu-panda-skill-harness)

```python
scorer=gla_scorer(config=config, text_source="artifacts")
```

### Re-scoring an existing log from the CLI

Once installed, scorers are registered via Inspect's entry point system:

```bash
inspect score logs/my-eval.eval --scorer learning_commons_inspect_scorers/gla_scorer
```

## Configuration

| Parameter | Default | Description |
|---|---|---|
| `config` | env vars | `EvaluatorConfig`. If `None`, reads `GOOGLE_API_KEY`, `ANTHROPIC_API_KEY`, or `OPENAI_API_KEY` from the environment. |
| `text_source` | `"completion"` | `"completion"` scores `state.output.completion`; `"artifacts"` joins `state.metadata["artifacts"]` file contents. |
| `target_grade_key` | `"target_grade"` | Metadata key holding the expected grade band. |
| `allow_adjacent` | `True` | If `True`, the one grade band above or below the target also passes. |

## Development

```bash
# From repo root
pip install -e sdks/python
pip install -e "integrations/inspect-python[dev]"
pytest integrations/inspect-python/tests/
```
