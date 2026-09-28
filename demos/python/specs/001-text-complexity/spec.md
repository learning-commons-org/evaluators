# Feature Specification: Text Complexity Demo

**Feature ID**: `001-text-complexity`
**Branch**: `ahussain/python-demo-text-complexity`
**Created**: 2026-09-28
**Status**: Implemented (local SDK build)
**Input**: "Build a minimal Python SDK demo, like the TS SDK demo, that runs every text
complexity evaluator against one text and grade and shows each result in an accordion.
Functional and usable, not fancy."

## ⚡ Guidelines

- The first feature of `demos/python/`, so it also establishes the app shell. There is no
  separate scaffold feature.
- The demo exercises the `learning-commons-evaluators` package the way an integrator would,
  written from the Python SDK README. A gap between the README and the package's behaviour is
  a finding, not something the demo papers over.
- Focus on WHAT the demo provides and WHY, not implementation detail.

## User Scenarios & Testing *(mandatory)*

### Primary User Story

A developer wants to see the Python SDK's text complexity family working through a browser.
They install the demo against the SDK package, provide their Google and OpenAI keys, and start
the app. On a single page they paste a text, pick a grade, and run. Every text complexity
evaluator runs against that input, and each one's result appears in its own collapsible
section: the verdict, the reasoning, what ran and what it cost, and the raw response the SDK
returned.

### Acceptance Scenarios

1. **Given** the app is running with both keys configured, **When** the developer opens the
   app root, **Then** a page renders with a text area, a grade selector offering grades 3–12,
   and a run button.
2. **Given** a non-empty text and a grade, **When** the developer runs, **Then** all eight text
   complexity evaluators run against it and one collapsible section per evaluator appears, in a
   fixed order, each labelled with the evaluator's name and its headline verdict.
3. **Given** a completed run, **When** the developer expands an evaluator's section, **Then** it
   shows the evaluator's full result payload, the model that ran, processing time, input and
   output token counts, and the raw result envelope as formatted JSON.
4. **Given** a completed run, **When** the developer looks at the Grade Level Appropriateness
   section, **Then** it states that this evaluator judged the text alone (it determines a grade
   band rather than judging against the selected grade) and shows the band it returned.
5. **Given** one evaluator fails (bad key, provider error, invalid output), **When** the run
   completes, **Then** that evaluator's section shows the SDK error type and message, and every
   other evaluator's result still renders.
6. **Given** a completed run, **When** the page re-renders with results, **Then** the submitted
   text and grade remain in the form so the developer can tweak and re-run.
7. **Given** a run is in progress, **When** the developer waits, **Then** the page indicates that
   evaluation is running and the run button cannot be pressed again.

### Edge Cases

- Empty or whitespace-only text → a validation message; no evaluators run.
- Non-blank text shorter than 10 characters → Background Knowledge Demands, Grade Level
  Appropriateness, Meaning Directness and Sentence Structure reject it (their input schemas'
  minimum length is 10), while the other four, which accept one character, still run. This is
  the easiest way to see some panels fail and the rest render.
- A provider key missing from `.env` → the app still starts; evaluators needing that key show
  the SDK's `ConfigurationError` in their own section. Vocabulary Complexity needs both keys at
  every grade.
- Purpose Clarity returns `more_context_needed` → shown as its verdict like any other value.
- A very long text → passed to the SDK unchanged; any SDK rejection surfaces as that
  evaluator's error.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The app MUST be a single Python web server rendering HTML pages server-side; no
  separate frontend build or JavaScript framework.
- **FR-002**: The app MUST present one page at `/` with a text input, a grade selector limited
  to grades 3–12, and a run action.
- **FR-003**: A run MUST invoke all eight text complexity evaluators exported by the SDK:
  Background Knowledge Demands, Meaning Directness, Organizational Structure, Purpose Clarity,
  Reference Knowledge Demands, Sentence Structure, Vocabulary Complexity, and Grade Level
  Appropriateness.
- **FR-004**: Grade Level Appropriateness MUST receive the text only; the other seven MUST
  receive the text and the selected grade.
- **FR-005**: The evaluators MUST run concurrently, so total wait is roughly the slowest
  evaluator rather than the sum.
- **FR-006**: Each evaluator's outcome MUST be isolated: an exception from one MUST NOT prevent
  the others from completing or rendering.
- **FR-007**: Results MUST render as one collapsible section per evaluator, in a fixed order,
  each summarising its headline verdict (`complexity_score`, or `grade_band` for Grade Level
  Appropriateness) without being expanded.
- **FR-008**: An expanded successful section MUST show every field of the evaluator's result
  payload, the model, processing time, token usage, and the full result envelope as JSON.
- **FR-009**: A failed section MUST show the SDK exception's class name and message.
- **FR-010**: Provider keys MUST be loaded from a `.env` file, with a checked-in
  `.env.example`, and passed to the SDK explicitly (the SDK does not read them from the
  environment). Keys MUST never reach the browser.
- **FR-011**: The demo MUST depend on the SDK as an installed package, never by importing from
  `sdks/python/src`. Switching to the published release of this SDK MUST be a dependency-declaration change only, with no
  application code change.

- **FR-012**: Empty or whitespace-only text MUST be rejected before any evaluator runs, with
  one validation message rather than eight identical per-evaluator errors.
- **FR-013**: The demo MUST leave SDK telemetry at its default (enabled), as an integrator's
  code would, and its README MUST say so and point to the SDK's `telemetry` option.

### Key Entities

- **EvaluatorRun**: one evaluator's outcome in a run — the evaluator's display name, and either
  its `EvaluationResult` or the exception it raised. Runs are shown in a fixed order: Grade Level
  Appropriateness, Background Knowledge Demands, Vocabulary Complexity, Sentence Structure,
  Meaning Directness, Purpose Clarity, Organizational Structure, then Reference Knowledge
  Demands.

## Out of Scope

- A page per evaluator, or evaluator families other than text complexity.
- Batch evaluation, model overrides, streaming or progressive results.
- A CI workflow for the demo. It follows once the demo installs the published release.
- Deployment; the demo runs locally only.

## Review & Acceptance Checklist

- [x] No implementation detail leaks into requirements (the server-rendered constraint is a
      stated project choice).
- [x] Requirements are testable and unambiguous.
- [x] Acceptance scenarios cover the happy path, per-evaluator failure, and input validation.
- [x] The switch to the published release is captured as open work in `tasks.md`.

## Execution Status

- [x] Scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [ ] Implemented and verified
