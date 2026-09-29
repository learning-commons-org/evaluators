# Implementation Plan: Text Complexity Demo

**Feature ID**: `001-text-complexity`
**Date**: 2026-09-28
**Spec**: [spec.md](./spec.md)
**Depends on**: none (first feature of `demos/python/`)

## Summary

A single FastAPI app that renders one Jinja page. The form posts text and grade; the handler
runs all eight text complexity evaluators concurrently with `asyncio.gather`, catching each
evaluator's exception separately, and re-renders the page with one `<details>` accordion per
evaluator. The SDK is installed as a package: the published 1.x release from PyPI. Until that
release shipped it was built from `sdks/python` (see Phase 0).

## Technical Context

- **Language**: Python 3.11+ (the SDK's floor).
- **Web**: FastAPI, served by Uvicorn; Jinja2 templates; `python-multipart` for form posts;
  `python-dotenv` for `.env`.
- **SDK surface** (from `sdks/python/README.md`):
  - Constructors take keys as keywords: `google_api_key=`, `openai_api_key=`. A missing key,
    or one passed as `None` or blank, raises `ConfigurationError` at construction. A key the
    evaluator does not use is ignored, not rejected (`evaluators/base.py`,
    `_validate_credentials`), so every constructor can receive both keys.
  - For every text complexity evaluator `aclose()` is the inherited no-op; only Math
    Standards Alignment owns a client that needs closing. Constructing per request without
    `async with` leaks nothing.
  - `await evaluator.evaluate(text=..., grade_level=...)`; Grade Level Appropriateness takes
    `text=` only.
  - Returns `EvaluationResult`: `.evaluator`, `.result` (pydantic payload), `.metadata`
    (`model`, `processing_time_ms`, `token_usage.input_tokens` / `.output_tokens`).
  - `read_outcome(evaluation, Cls.metadata.outcome).score` gives the headline for every
    evaluator in the family: its contract declares `complexity_score` for seven and
    `grade_band` for Grade Level Appropriateness.
- **Keys**: `GOOGLE_API_KEY`, `OPENAI_API_KEY`; optional `TELEMETRY_LEARNING_COMMONS_API_KEY`
  for identified telemetry. The name mirrors the SDK setting it feeds,
  `telemetry.learning_commons_api_key`, and leaves `LEARNING_COMMONS_API_KEY` for Learning
  Commons API calls (Knowledge Graph, Math Standards Alignment), as the TypeScript demo uses
  it.
- **Telemetry**: every constructor takes `telemetry=True | False | TelemetryOptions(...)`.
  `TelemetryOptions(learning_commons_api_key=...)` opts in to identified telemetry; the SDK
  forwards it to the telemetry client (`evaluators/base.py`), which sends it as the
  `X-API-Key` header.
- **Tooling**: plain `venv` + `pip`, as `sdks/python` uses. Ruff for lint and format; pytest
  with FastAPI's `TestClient` for the tests.

## Constitution Check

- **Spec-driven**: spec → plan → tasks → code; this spec lives under `demos/python/specs/`,
  separate from the TS demo's. ✅
- **Integrator's view**: the SDK is imported only as an installed package, written against
  the README; anything the README gets wrong or leaves out is recorded as a finding. ✅
- **No version pins in docs**: versions appear in the requirements files only. ✅
- **Definition of done**: `ruff check`, `ruff format --check`, and `pytest` pass; plus a
  live smoke run with real keys. The TS demo has no test suite; this one adds a small one
  because the per-evaluator isolation logic is easy to break and cheap to test offline. ✅

## Project Structure

### Documentation (this feature)

```
demos/python/specs/001-text-complexity/
  spec.md  plan.md  tasks.md
```

### Source code (created by this feature)

```
demos/python/
  app.py                 # FastAPI app: GET / (empty form), POST / (run + results)
  test_app.py            # TestClient tests with evaluators stubbed
  templates/index.html   # form + accordions; inline CSS and one onsubmit handler
  requirements.txt       # runtime: fastapi, uvicorn, jinja2, python-multipart,
                         #   python-dotenv, learning-commons-evaluators>=1.0.0
                         #   (../../sdks/python until the 1.x release shipped)
  requirements-dev.txt   # -r requirements.txt, pytest, httpx, ruff
  ruff.toml              # py311, line length 100, the SDK's rule selection
  .env.example           # GOOGLE_API_KEY=, OPENAI_API_KEY=, TELEMETRY_LEARNING_COMMONS_API_KEY=
  .gitignore             # .env, .venv/, __pycache__/
  README.md              # what it is, install, keys, run, test
  CLAUDE.md              # verify commands; spec-driven note (mirrors demos/typescript)
```

Repo root `CLAUDE.md`: add `demos/python/` to the Layout table and its verify command to the
per-workspace table.

## Phase 0: Research

- **The SDK is already on PyPI, at the same version number.** `.release-please-manifest.json`
  and `sdks/python/CHANGELOG.md` show 0.1.0–0.2.1 released, and `sdks/python/pyproject.toml`
  on this branch still says `0.2.1`. So a wheel built from the branch and PyPI's 0.2.1 share a
  version pip cannot tell apart. An unbounded `learning-commons-evaluators` requirement plus
  "install the local wheel first" would silently give a fresh venv the old PyPI release, which
  predates this branch's API. The version is release-please's to set, so it is not bumped here.
- **Local SDK install (FR-011).** `requirements.txt` names the SDK by path:
  `../../sdks/python`. pip resolves that relative to the working directory, so installs run
  from `demos/python/`. pip builds a regular (non-editable) wheel from the directory and
  installs it, so the demo gets what an integrator gets: package data included, nothing
  imported from the source tree, and no way to fall back to PyPI's 0.2.1. After changing SDK
  source, `pip install --force-reinstall --no-deps ../../sdks/python` refreshes it. The
  bundled contracts and generated schemas are committed, so no `make build` is needed first.
  `[tool.setuptools.package-data]` includes `contracts/_generated/**/*.json` and `*.txt`.
  That was checked statically only, because the review sandbox had no network, so T003 builds
  and imports the package to confirm it.
- **Switching to PyPI** replaces that one line with `learning-commons-evaluators>=<first
  release carrying this API>`: a dependency-declaration change only. The README describes the
  path install for now; the final task rewrites that section too.
- **Resolved (T014).** The 1.x release is published, so `requirements.txt` now reads
  `learning-commons-evaluators>=1.0.0`, which PyPI's 0.2.1 cannot satisfy. The demo was
  re-verified in a fresh venv against the package installed from PyPI, not a local path.
- **Construction inside the isolated task.** Constructing an evaluator raises
  `ConfigurationError` when a key is missing. Evaluators are therefore constructed per run,
  inside the same `try` as `evaluate`, so a missing key fails only that evaluator's panel
  (spec edge case) instead of crashing startup. Construction builds provider clients, which is
  trivial next to an LLM call.
- **Headline via `read_outcome`.** Using the README's generic accessor instead of reading
  `complexity_score`/`grade_band` by name means the page needs no per-evaluator table and
  exercises a documented SDK feature.
- **Payload rendering.** `evaluation.model_dump()["result"]` gives every payload field for the
  detail table (lists such as Vocabulary Complexity's `tier_2_words` render as
  comma-separated values); `evaluation.model_dump_json(indent=2)` gives the raw envelope.
- **Telemetry** stays on, as for an integrator. The README says so and shows how to turn it
  off. Anonymous events carry only a per-machine client id and `sdk_version`, and this branch
  reports the same `sdk_version` as PyPI's 0.2.1, so the demo's events cannot be told apart
  from other anonymous traffic. Passing the optional `TELEMETRY_LEARNING_COMMONS_API_KEY` as
  `TelemetryOptions(learning_commons_api_key=...)` attributes them to a Learning Commons user
  (FR-014). The SDK has no field naming the calling application, so identifying the user is
  as specific as it gets.
- **In-progress state (spec scenario 7).** A synchronous form post already keeps the page
  waiting. A few lines of inline `onsubmit` disable the button and show "Running…". That is
  plain JavaScript, not a framework, so FR-001 still holds.

## Phase 1: Design

### Request flow

```
GET  /  → render index.html(text=DEFAULT_TEXT, grade=DEFAULT_GRADE (4), runs=None)
POST /  form: text: Annotated[str, Form()] = ""
              grade: Annotated[int, Form(ge=3, le=12)]
        text.strip() == ""        → render with error message, runs=None
        grade not in 3..12        → 422 from FastAPI validation
        otherwise                 → runs = await run_all(text, grade)
                                    render index.html(text, grade, runs)
```

### `app.py` shape

```python
EVALUATORS: list[tuple[type[BaseEvaluator], bool]] = [
    # (class, takes grade_level); display name is cls.metadata.name
    (BackgroundKnowledgeDemandsEvaluator, True),
    ...(GradeLevelAppropriatenessEvaluator, False),
]


@dataclass
class EvaluatorRun:
    name: str
    takes_grade: bool
    evaluation: EvaluationResult | None
    headline: str | None
    error: BaseException | None


async def run_one(cls, takes_grade, text, grade) -> EvaluatorRun:
    name = cls.metadata.name
    try:
        evaluator = cls(google_api_key=..., openai_api_key=...)
        kwargs = {"text": text, "grade_level": grade} if takes_grade else {"text": text}
        evaluation = await evaluator.evaluate(**kwargs)
        headline = read_outcome(evaluation, cls.metadata.outcome).score
        return EvaluatorRun(name, takes_grade, evaluation, headline, None)
    except Exception as exc:
        return EvaluatorRun(name, takes_grade, None, None, exc)


async def run_all(text, grade) -> list[EvaluatorRun]:
    return await asyncio.gather(*(run_one(c, g, text, grade) for c, g in EVALUATORS))
```

- Every constructor receives both keys (unused keys are ignored; see Technical Context) and
  `telemetry=telemetry()`, which returns `TelemetryOptions(learning_commons_api_key=...)` when
  `TELEMETRY_LEARNING_COMMONS_API_KEY` is non-blank and `True` otherwise. It reads the module
  global at call time so the tests can monkeypatch it.
- Keys are read once at startup with `load_dotenv()` and `os.environ.get(...)`. A missing key
  is passed as `None` and left to the SDK to reject, which exercises its documented error.
- `EVALUATORS` is module-level so the tests can monkeypatch it with stub classes.

### `index.html` shape

- Form: `<textarea name="text" required>`, `<select name="grade">` 3–12, submit button.
- Results: one `<details>` per run. The `<summary>` shows the name, headline or "error", the
  model and the time taken. The body shows either a payload key/value table, a tokens line and
  `<pre>` raw JSON, or the error's `type(exc).__name__` and `str(exc)`. The Grade Level
  Appropriateness panel carries a one-line note that it judged the text alone.
- Styling: a small inline `<style>` block. No external assets.

### Tests (`test_app.py`)

Offline, with `EVALUATORS` monkeypatched to stubs that return a real `EvaluationResult` or
raise:

1. `GET /` renders the form with grades 3–12.
2. `POST /` with whitespace text shows the validation message and calls no evaluator.
3. `POST /` with one stub raising `ConfigurationError` and the rest succeeding renders every
   panel; the failing one shows `ConfigurationError` and its message.
4. The text-only stub receives no `grade_level`; the others receive the selected grade.
5. The submitted text and grade are echoed back into the form.
6. `EVALUATORS` lists exactly the eight text complexity classes (guards FR-003).
7. Every evaluator receives both provider keys and `telemetry=True` when no Learning Commons
   key is set, and `TelemetryOptions(learning_commons_api_key=...)` when one is (FR-014).

## Phase 2: Task Planning Approach

Tasks go in `tasks.md` in dependency order: scaffold and requirements, then the SDK install
check, app and template, tests, docs, the verification gates, and the live smoke run. The
last task moves to the published package and re-verifies; it is done.

## Risks

- **Same-version collision with PyPI's 0.2.1** (see Phase 0). Avoided by the path
  requirement, then removed by T014's `>=1.0.0` bound. Resolved.
- **Release branch drift.** The branch was cut from a local copy of `release-python-sdk-1.0`
  while GitHub was unreachable. Rebased onto the release branch, and then onto `main` once it
  merged. Resolved.
- **Provider rate limits** with eight concurrent calls on low-tier keys. Each one surfaces
  as a per-panel `RateLimitError`; no demo-side throttling.
