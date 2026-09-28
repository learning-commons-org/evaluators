# Text Complexity Demo — Python SDK

A single web page running every text complexity evaluator in the `learning-commons-evaluators` Python SDK against one text. Each evaluator appears in its own collapsible section with its verdict, reasoning, the model, its token usage, and the raw response envelope. The demo installs the SDK as a package, the way an integrator would.

## Setup

Requires Python 3.11+. From `demos/python/`:

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`requirements.txt` currently builds the SDK from `../../sdks/python` because this release is not yet on PyPI. Once the SDK is published, this file will reference the published version instead.

After SDK source changes, refresh the local install:

```shell
pip install --force-reinstall --no-deps ../../sdks/python
```

## Keys

Copy `.env.example` to `.env` and add your keys:

| Key                                  | Used for                                                     |
| ------------------------------------ | ------------------------------------------------------------ |
| `GOOGLE_API_KEY`                     | All evaluators except Sentence Structure                     |
| `OPENAI_API_KEY`                     | Sentence Structure and Vocabulary Complexity                 |
| `TELEMETRY_LEARNING_COMMONS_API_KEY` | Optional: attributes telemetry to your Learning Commons user |

A missing provider key fails only the evaluators that need it, with the SDK's `ConfigurationError`. The app continues and shows the error in that evaluator's section.

## Run

```shell
uvicorn app:app --reload
```

Open http://localhost:8000. Paste a text, select a grade, and click Evaluate.

Each run makes ten paid model calls: one for each evaluator, except Sentence Structure and Vocabulary Complexity, which each make two.

## Telemetry

The SDK sends usage telemetry by default, and this demo leaves it on, as an integrator's code would. Without `TELEMETRY_LEARNING_COMMONS_API_KEY` the events are anonymous; with it set, the demo passes it as `TelemetryOptions(learning_commons_api_key=...)`, so every event is attributed to your Learning Commons user. See the [SDK README's Telemetry section](../../sdks/python/README.md#telemetry) for what is sent and how to disable it with `telemetry=False`.

## Test

```shell
pip install -r requirements-dev.txt
ruff check .
ruff format --check .
pytest -q
```
