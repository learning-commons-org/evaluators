# Local development

## Package layout

- **`contracts/`** — The `evals/` registry as the package ships it. `contracts/_generated/<family>/<subject>/<evaluator>/` holds each contract's `config.json`, input and output schemas, and prompt files, copied verbatim by `make generate-contracts`; `contracts/loader.py` reads one back as a typed `Contract`.
- **`schemas/<family>/<subject>/<evaluator>.py`** — Generated from each contract's schemas: pydantic `<Class>Input` and `<Class>Output` models.
- **`providers/`** — The `LLMProvider` protocol and one adapter per native SDK (`openai_sdk.py`, `anthropic_sdk.py`, `google_genai.py`), `create_provider()`, and the resampling half of the retry split (`retry.py`).
- **`evaluators/`** — `BaseEvaluator` (config checks, provider construction), `SingleStepEvaluator` (the one-model-call flow), `MultiStepEvaluator` (steps in declared order, skipping any whose `condition` the inputs miss; placeholders resolved from inputs, preprocessing, and earlier steps' outputs), `inputs.py` (§4.1 validation), `registry.py` (`get_evaluators`, `get_evaluator` with `id_history`), and the concrete evaluators in nested `<family>/<subject>/` packages mirroring `evals/`. Both bases are declarative: an evaluator names its contract and its generated models, and everything else is read from the contract at class creation.
- **`config.py`** — `EvaluatorConfig`, `ModelOverride`, `TelemetryOptions` (SDK spec §3).
- **`schemas/evaluator.py`, `schemas/outcome.py`, `schemas/metadata.py`** — The result envelope, `read_outcome`, and static `EvaluatorMetadata`.
- **`features/`** — Contract-declared preprocessing bound into prompts: library computations (`textstat` Flesch-Kincaid) in `preprocessing.py`, and the functions a `custom` entry names — `readability.py` (the ground-truth counts block) and `sentence_features.py` (the ratios derived from a step's counts).
- **`prompts/`** — Placeholder substitution, identical to the TypeScript renderer.
- **`errors.py`** — The canonical error taxonomy (SDK spec §6) and `wrap_provider_error()`.
- **`logger.py`** — Logging helpers following the stdlib library convention (`NullHandler`, no root configuration)
- **`version.py`** — Package version and description

Telemetry emission, the Knowledge Graph client, and batch evaluation land in the following PRs.

## Development setup

```bash
cd sdks/python

python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate.bat  # Windows CMD
# .venv\Scripts\Activate.ps1  # Windows PowerShell

pip install -e ".[dev]"

make verify   # check-build + lint + format-check + typecheck + pip-check + test (same gate as CI)
make test     # pytest only
```

From `sdks/python/`:

- `make lint` — Ruff on `src/` and `tests/`
- `make format` / `make format-check` — Ruff formatter
- `make typecheck` — Mypy
- `make pip-check` — `pip check`
- `make coverage` — tests with coverage report

## Using the SDK before publishing

```bash
pip install -e /path/to/evaluators/sdks/python
```

Editable install: changes to SDK source apply without reinstalling.

## Regenerating after a change under `evals/`

The registry at `evals/<family>/<subject>/<evaluator>/` is the source of truth for every evaluator's id, prompts, models, preprocessing, and schemas. The package bundles it and generates pydantic models from it, so after editing anything there:

```bash
make generate-contracts  # bundle contracts into contracts/_generated/ and regenerate schemas/<family>/<subject>/*.py
make check-generated     # verify the committed files match evals/ (CI runs this; stale or orphaned files fail)
```

The generator (`scripts/generate_contracts.py`) checks each prompt and rubric file against the `sha256` its `config.json` declares and refuses to bundle one that drifted. Commit the registry change together with the regenerated files; `.gitattributes` marks them `linguist-generated=true` so GitHub collapses them in review.

Generated schema modules start with `# GENERATED — do not edit directly.` and are excluded from Ruff; edit the `output_schema.json` or `input_schema.json` they come from instead. Bundled files are byte-for-byte copies.

## Tests

- `tests/unit/errors/` — the taxonomy's rules and the error mapping check: every signal row of SDK spec §6.5 maps to the expected class, using the native SDKs' real exception types.
- `tests/unit/providers/` — each adapter against a fake client, the factory, and the resampling loop.
- `tests/unit/contracts/` — every bundled contract read back and cross-checked against `evals/` (sha256, placeholder sources, outcome fields), plus the generator's emitter on synthetic schemas.
- `tests/unit/schemas/` — parser tests: hand-written payloads per `output_schema.json` against the generated `<Class>Output` models.
- `tests/unit/evaluators/` — the single-step and multi-step flows on synthetic contracts, config and `model_override` checks, input validation, the registry, and `test_registry_conformance.py`: every contract in `evals/` has a registered class or an entry in its `UNIMPLEMENTED` allowlist, and porting an evaluator without deleting its entry fails the build.
- `tests/unit/test_cross_sdk_prompts.py` — for every fixture, and every step the inputs run, Python renders the prompt the TypeScript renderer would. Placeholders each SDK computes with its own language's library are masked, and so are step outputs, which would mean calling a model; the masked numbers' rounding is checked separately in the same file.
- `tests/integration/` — live provider calls driven by `evals/**/fixtures.json`, skipped unless `RUN_INTEGRATION_TESTS=1` and the provider keys are set (`make integration-test`).

## Adding an evaluator

1. The contract exists under `evals/<family>/<subject>/<evaluator>/` (that is the registry's job). Run `make generate-contracts` so its bundle and `<Class>Input` / `<Class>Output` models exist.
2. Add `evaluators/<family>/<subject>/<evaluator>.py` declaring the class. For a contract with one step:

   ```python
   class PurposeClarityEvaluator(SingleStepEvaluator[PurposeClarityInput, PurposeClarityOutput]):
       contract = load_contract(EVALUATOR_ID)
       input_model = PurposeClarityInput
       output_model = PurposeClarityOutput
   ```

   For a contract with several, add `step_models` naming every declared step — `None` for one
   that answers in prose — and `computations` for any function a `custom` preprocessing entry
   names, keyed by the name it declares:

   ```python
   class SentenceStructureEvaluator(
       MultiStepEvaluator[SentenceStructureInput, SentenceStructureOutput]
   ):
       contract = load_contract(EVALUATOR_ID)
       input_model = SentenceStructureInput
       output_model = SentenceStructureOutput
       step_models = {
           "sentence_analysis": SentenceAnalysis,
           "classify_complexity": SentenceStructureOutput,
       }
       computations = {"compute_ground_truth_counts": compute_ground_truth_counts, ...}
   ```

   A step's own output model has no schema in the registry, so it is written by hand beside
   the evaluator; the contract's `output_schema.json` describes the evaluator's result only.

3. Register it in `evaluators/registry.py` and export it (class, input, output) from `evaluators/__init__.py` and the package barrel.
4. Delete its id from `UNIMPLEMENTED` in `tests/unit/evaluators/test_registry_conformance.py`; the conformance, cross-SDK prompt, and integration suites pick it up automatically.
