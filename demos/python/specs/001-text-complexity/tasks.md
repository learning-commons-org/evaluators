# Tasks: Text Complexity Demo

**Feature ID**: `001-text-complexity`
**Input**: [spec.md](./spec.md), [plan.md](./plan.md)
**Prerequisite**: none

## Format: `[ID] [P?] [USER?] Description`

`[P]` = can run in parallel (different files, no dependency on an unfinished task).
`[USER]` = the implementer cannot do this step; stop and ask the user, and wait for them to
confirm it is done before continuing past it.

Run every command from `demos/python/` unless a task says otherwise. The venv is created with
`python3.12` because the SDK requires Python 3.11+ and this machine's default `python3` is
3.10; after T002, activate it once per shell with `source .venv/bin/activate`. Every `pip`
command needs network access to PyPI. Do not write a dependency version into any doc or spec,
and do not edit anything under `sdks/`. The implementer cannot read or write `.env` files.

## Phase 3.1: Setup

- [x] T001 (SKIPPED: network down) From the repo root: `git fetch origin release-python-sdk-1.0` then
      `git rebase origin/release-python-sdk-1.0`. The branch was cut from a stale local copy
      while GitHub was unreachable.
      **Pass**: `git log -1 --format=%H origin/release-python-sdk-1.0` equals
      `git merge-base HEAD origin/release-python-sdk-1.0`. If the fetch fails for network
      reasons, stop and tell the user; do not continue on the stale base.
- [x] T002 Create the dependency files and the venv:
      - `requirements.txt`, exactly these lines, unpinned:
        ```
        fastapi
        uvicorn
        jinja2
        python-multipart
        python-dotenv
        ../../sdks/python
        ```
      - `requirements-dev.txt`:
        ```
        -r requirements.txt
        pytest
        httpx
        ruff
        ```
      - `ruff.toml`:
        ```toml
        target-version = "py311"
        line-length = 100

        [lint]
        select = ["E", "W", "F", "I", "UP", "B", "SIM"]
        ignore = ["E501"]
        ```
      - `.gitignore`: `.env`, `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`,
        one per line.
      - `.env.example`:
        ```
        # Google Gemini: every text complexity evaluator except Sentence Structure
        GOOGLE_API_KEY=
        # OpenAI: Sentence Structure and Vocabulary Complexity
        OPENAI_API_KEY=
        ```
      Then run `python3.12 -m venv .venv`, `source .venv/bin/activate`,
      `pip install -r requirements-dev.txt`.
      **Pass**: install exits 0 and `pip show learning-commons-evaluators` prints a
      `Location:` inside `.venv`, not `sdks/python/src` (a regular install, not editable).
- [x] T003 Confirm the installed SDK is complete and is this branch's code, not PyPI's 0.2.1:
      ```
      python -c "import learning_commons_evaluators as m, pathlib; p = pathlib.Path(m.__file__).parent / 'contracts/_generated/text_complexity/ela_reading'; print(sorted(d.name for d in p.iterdir())); from learning_commons_evaluators import GradeLevelAppropriatenessEvaluator, read_outcome, get_evaluators; print(GradeLevelAppropriatenessEvaluator.metadata.outcome.score)"
      ```
      **Pass**: the first line lists exactly `background_knowledge_demands`,
      `grade_level_appropriateness`, `meaning_directness`, `organizational_structure`,
      `purpose_clarity`, `reference_knowledge_demands`, `sentence_structure`,
      `vocabulary_complexity`; the second line is `grade_band`. An `ImportError` means an
      old SDK was installed: stop and report it.

## Phase 3.2: App

- [x] T004 Create `app.py` with exactly this content:
      ```python
      import asyncio
      import os
      from dataclasses import dataclass
      from pathlib import Path
      from typing import Annotated, Any

      from dotenv import load_dotenv
      from fastapi import FastAPI, Form, Request
      from fastapi.responses import HTMLResponse
      from fastapi.templating import Jinja2Templates
      from learning_commons_evaluators import (
          BackgroundKnowledgeDemandsEvaluator,
          BaseEvaluator,
          EvaluationResult,
          GradeLevelAppropriatenessEvaluator,
          MeaningDirectnessEvaluator,
          OrganizationalStructureEvaluator,
          PurposeClarityEvaluator,
          ReferenceKnowledgeDemandsEvaluator,
          SentenceStructureEvaluator,
          VocabularyComplexityEvaluator,
          read_outcome,
      )

      load_dotenv()
      GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
      OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

      GRADES = range(3, 13)
      DEFAULT_GRADE = 5

      # (class, takes grade_level). Grade Level Appropriateness determines a grade band from
      # the text alone, so it is the one evaluator not given the selected grade.
      EVALUATORS: list[tuple[type[BaseEvaluator], bool]] = [
          (GradeLevelAppropriatenessEvaluator, False),
          (BackgroundKnowledgeDemandsEvaluator, True),
          (VocabularyComplexityEvaluator, True),
          (SentenceStructureEvaluator, True),
          (MeaningDirectnessEvaluator, True),
          (PurposeClarityEvaluator, True),
          (OrganizationalStructureEvaluator, True),
          (ReferenceKnowledgeDemandsEvaluator, True),
      ]


      @dataclass
      class EvaluatorRun:
          name: str
          takes_grade: bool
          evaluation: EvaluationResult[Any] | None = None
          headline: str | None = None
          error: Exception | None = None

          @property
          def payload(self) -> dict[str, Any]:
              return self.evaluation.model_dump()["result"] if self.evaluation else {}

          @property
          def envelope_json(self) -> str:
              return self.evaluation.model_dump_json(indent=2) if self.evaluation else ""


      async def run_one(
          cls: type[BaseEvaluator], takes_grade: bool, text: str, grade: int
      ) -> EvaluatorRun:
          run = EvaluatorRun(name=cls.metadata.name, takes_grade=takes_grade)
          # Constructed here, not at startup, so a missing key fails only this evaluator.
          try:
              evaluator = cls(google_api_key=GOOGLE_API_KEY, openai_api_key=OPENAI_API_KEY)
              inputs: dict[str, Any] = {"text": text}
              if takes_grade:
                  inputs["grade_level"] = grade
              run.evaluation = await evaluator.evaluate(**inputs)
              run.headline = read_outcome(run.evaluation, cls.metadata.outcome).score
          except Exception as exc:
              run.error = exc
          return run


      async def run_all(text: str, grade: int) -> list[EvaluatorRun]:
          return list(await asyncio.gather(*(run_one(cls, g, text, grade) for cls, g in EVALUATORS)))


      app = FastAPI()
      templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


      def render(
          request: Request,
          text: str = "",
          grade: int = DEFAULT_GRADE,
          runs: list[EvaluatorRun] | None = None,
          error: str | None = None,
          status_code: int = 200,
      ) -> HTMLResponse:
          context = {"text": text, "grade": grade, "grades": GRADES, "runs": runs, "error": error}
          return templates.TemplateResponse(request, "index.html", context, status_code=status_code)


      @app.get("/", response_class=HTMLResponse)
      async def index(request: Request) -> HTMLResponse:
          return render(request)


      @app.post("/", response_class=HTMLResponse)
      async def evaluate(
          request: Request,
          grade: Annotated[int, Form(ge=3, le=12)],
          text: Annotated[str, Form()] = "",
      ) -> HTMLResponse:
          if not text.strip():
              return render(request, text, grade, error="Enter some text to evaluate.", status_code=400)
          return render(request, text, grade, runs=await run_all(text, grade))
      ```
      Pass `text` to the SDK unstripped; the strip is only the emptiness check.
- [x] T005 [P] Create `templates/index.html`: one HTML5 page titled
      `Text Complexity — Python SDK demo`, no external assets, no JavaScript beyond the
      `onsubmit` below. Structure, in order:
      1. `<h1>Text Complexity</h1>` and one sentence: "Runs every text complexity evaluator in
         the `learning-commons-evaluators` Python SDK against one text."
      2. If `error`: `<p class="error">{{ error }}</p>`.
      3. `<form method="post" action="/" onsubmit="this.querySelector('button').disabled = true; this.querySelector('button').textContent = 'Running…';">`
         containing: a labelled `<textarea name="text" rows="12" required>{{ text }}</textarea>`
         (full width); a labelled `<select name="grade">` looping `grades`, with `selected` on
         the option equal to `grade`, labels `Grade 3` … `Grade 12`; and
         `<button type="submit">Evaluate</button>`.
      4. If `runs`: for each `run` in `runs`, one `<details>`:
         - `<summary>`: `<strong>{{ run.name }}</strong>`, then either `{{ run.headline }}` or,
           when `run.error`, `<span class="error">error</span>`. On success also add, muted,
           `{{ run.evaluation.metadata.model }} · {{ run.evaluation.metadata.processing_time_ms }} ms`.
         - If `not run.takes_grade`: `<p class="note">Judged on the text alone: this evaluator
           determines a grade band rather than judging against the selected grade.</p>`
         - On error: `<p class="error"><code>{{ run.error.__class__.__name__ }}</code>:
           {{ run.error }}</p>`.
         - On success: a two-column `<table>` of `run.payload.items()`. Render a list value
           as its items joined by `, ` (`{% if value is iterable and value is not string and value is not mapping %}`),
           anything else as-is. Then a line `Tokens: {{ …input_tokens }} in /
           {{ …output_tokens }} out` from `run.evaluation.metadata.token_usage`, then
           `<pre>{{ run.envelope_json }}</pre>`.
      Style it with one inline `<style>` block: system font stack, `max-width: 60rem`, centred;
      `.error` in red; `.note` and the muted summary text in grey; `pre` scrolls
      horizontally with a light background; table cells padded with a bottom border, first
      column bold and top-aligned. Leave Jinja autoescaping on (the default): do not use
      `|safe`.

## Phase 3.3: Tests

- [x] T006 Create `test_app.py`. Build stubs from the real classes so names, ids, and
      outcome fields come from the SDK:
      ```python
      def make_stub(real_cls, calls, fail=None):
          outcome = real_cls.metadata.outcome

          class Stub:
              metadata = real_cls.metadata

              def __init__(self, **keys):
                  if fail is not None:
                      raise fail

              async def evaluate(self, **inputs):
                  calls[real_cls.metadata.name] = inputs
                  return EvaluationResult(
                      evaluator=real_cls.metadata.id,
                      result={outcome.score: "stub_score", outcome.reasoning: "stub reasoning"},
                      metadata=EvaluationMetadata(
                          model="stub:model",
                          processing_time_ms=1,
                          token_usage=EvaluationTokenUsage(input_tokens=3, output_tokens=4),
                      ),
                  )

          return Stub
      ```
      A fixture monkeypatches `app.EVALUATORS` to
      `[(make_stub(cls, calls), takes_grade) for cls, takes_grade in original]` and yields
      `(TestClient(app.app), calls)`. Tests:
      1. `GET /` → 200; body contains `name="text"`, `Grade 3` and `Grade 12`, not
         `Grade 2` or `Grade 13`.
      2. `POST /` with `text="   "`, `grade=5` → 400; body contains
         `Enter some text to evaluate.`; `calls` is empty.
      3. `POST /` with `grade=13` → 422.
      4. Replace the Sentence Structure stub with
         `make_stub(SentenceStructureEvaluator, calls, fail=ConfigurationError("missing openai_api_key"))`.
         a. `asyncio.run(app.run_all("Some text to evaluate.", 5))` → 8 runs; exactly one has
            `isinstance(run.error, ConfigurationError)` (the Sentence Structure one), and the
            other seven have `evaluation` set, `error` `None`, `headline == "stub_score"`.
         b. `POST /` with the same text → 200; body contains `ConfigurationError`,
            `missing openai_api_key`, and exactly 8 occurrences of `<details`.
      5. `POST /` with `grade=7` → the Grade Level Appropriateness entry in `calls` is exactly
         `{"text": <text>}`, and each of the other seven is `{"text": <text>, "grade_level": 7}`.
      6. `POST /` with `grade=7` echoes the submitted text inside the textarea, and the grade-7
         option carries a `selected` attribute: assert with
         `re.search(r'<option[^>]*value="7"[^>]*selected', body)`, not a literal string.
      7. Without the fixture: `{cls.metadata.id for cls, _ in app.EVALUATORS}` equals
         `{m.id for m in get_evaluators() if m.id.startswith("text_complexity.")}`, and has
         length 8.
      Run `pytest -q`. **Pass**: 7 passed, no network calls.

## Phase 3.4: Docs

- [x] T007 [P] `README.md` with these sections, no dependency versions:
      - One paragraph: what the demo is (one page, every text complexity evaluator, one
        accordion each) and that it installs the SDK as a package, as an integrator would.
      - **Setup**: Python 3.11+; from `demos/python/`, `python3 -m venv .venv`,
        `source .venv/bin/activate`, `pip install -r requirements.txt`. State that
        `requirements.txt` currently builds the SDK from `../../sdks/python` because this
        release is not yet on PyPI, and that after SDK source changes
        `pip install --force-reinstall --no-deps ../../sdks/python` refreshes it.
      - **Keys**: copy `.env.example` to `.env`; a table of `GOOGLE_API_KEY` and
        `OPENAI_API_KEY` with which evaluators need each. A missing key fails only the
        evaluators that need it, with the SDK's `ConfigurationError`.
      - **Run**: `uvicorn app:app --reload`, then open http://localhost:8000. One run makes
        ten paid model calls: one each, except Sentence Structure and Vocabulary Complexity,
        which make two.
      - **Telemetry**: the SDK sends anonymous usage telemetry by default and the demo
        leaves it on; link to the Telemetry section of `../../sdks/python/README.md` for what
        is sent and how to pass `telemetry=False`.
      - **Test**: `pip install -r requirements-dev.txt`, then `ruff check .`,
        `ruff format --check .`, `pytest -q`.
- [x] T008 [P] `CLAUDE.md`, mirroring `../typescript/CLAUDE.md`:
      ~~~markdown
      # demos/python

      FastAPI + Jinja demo of the `learning-commons-evaluators` Python SDK, installed as a package — never imported from `sdks/python/src`. It exercises the SDK the way an integrator would, so treat a gap found here as an SDK or README bug worth filing.

      ## Verify

      ```shell
      ruff check . && ruff format --check . && pytest -q
      uvicorn app:app --reload   # http://localhost:8000
      ```

      ## Spec-driven

      Features live in `specs/<nnn>-<slug>/` and progress spec → plan → tasks → implementation. Add a spec before building a feature here.
      ~~~
      Also update `../typescript/CLAUDE.md`'s sentence "This is the one place in the repo that
      uses spec-driven development." to "This and `demos/python/` are the places in the repo
      that use spec-driven development."
- [x] T009 [P] Root `CLAUDE.md` (at `../../CLAUDE.md`): add a row after `demos/typescript/`
      in the Layout table, `` | `demos/python/` | FastAPI + Jinja demo of the Python SDK | ``,
      and a row after it in the per-workspace table,
      `` | `demos/python/` | `ruff check . && ruff format --check . && pytest -q` | ``. Keep the
      tables aligned. Change nothing else.

## Phase 3.5: Verify

- [x] T010 Run `ruff format .`, then `ruff check .`, `ruff format --check .`, `pytest -q`,
      and from the repo root `python3 scripts/check.py`.
      **Pass**: all exit 0. Fix code, not the rules, if any fails.
- [x] T011 Offline boot check: `uvicorn app:app --port 8000` in the background, then
      `curl -s -o /dev/null -w '%{http_code}' localhost:8000/` → `200`, and
      `curl -s -X POST -d 'text=%20&grade=5' localhost:8000/ | grep -c 'Enter some text'` →
      `1`. Stop the server with `lsof -ti:8000 | xargs kill`.
- [ ] T012 [USER] (SKIPPED) Live run. Ask the user to create `.env` from `.env.example` with real keys,
      run `uvicorn app:app --reload`, open http://localhost:8000, paste a grade-appropriate
      passage of a few paragraphs, pick grade 5, and click Evaluate. This makes paid model
      calls. **Pass**: eight sections, each with a headline; Grade Level Appropriateness shows
      a band such as `4-5` with the text-alone note; Vocabulary Complexity's and Sentence Structure's model fields
      name every model that ran (joined by `+` when there are several); the raw JSON matches the README's `EvaluationResult` shape. Then
      a text under 10 characters: Background Knowledge Demands, Grade Level Appropriateness,
      Meaning Directness and Sentence Structure show `InputValidationError`, and the other four
      still render. Record any README mismatch in the PR description.
- [x] T013 Close out: tick the completed tasks in this file. In `spec.md`, tick the Review &
      Acceptance Checklist and set **Status** to `Implemented (local SDK build)`. Leave
      "Implemented and verified" unticked until T014.

## Phase 3.6: Published SDK (open until the release ships; blocks merging to `main`)

- [ ] T014 [USER] Once the release carrying this SDK API is on PyPI: in `requirements.txt`
      replace `../../sdks/python` with `learning-commons-evaluators>=<that version>`, rewrite
      the README's Setup note to drop the local-build text, recreate the venv from scratch
      (`rm -rf .venv`, then T002's venv commands), and rerun T003, T010, T011, and T012.
      **Pass**: `pip show learning-commons-evaluators` shows the published version; no
      application code changed. Then tick "Implemented and verified" in `spec.md` and set
      **Status** to `Implemented`.

## Dependencies

- T001 before everything. T002 → T003 → T004.
- T005 can run alongside T004; T006 needs both.
- T007–T009 are independent of the code and of each other.
- T010–T011 after T004–T009; T012 after T011; T013 after T012; T014 last, after release.

## Parallel Example

```
# Once T003 passes:
T004 alongside T005, T007, T008, T009
```
