# Feature Specification: Math Standards Alignment Evaluator Page

**Feature ID**: `002-math-standards-alignment`
**Branch**: `002-math-standards-alignment`
**Created**: 2026-07-16
**Status**: Implemented
**Input**: "Implement a Math Standard Alignment evaluator page — everything related to the
Math Standards Alignment evaluator goes here, plugged into the demo app scaffold (001)."

## ⚡ Guidelines

- Builds on `001-demo-app-scaffold`; adds one evaluator page + its API routes and the home
  registry entry.
- Focus on WHAT the page does and WHY. Alignment scoring itself is the SDK's concern.

## User Scenarios & Testing *(mandatory)*

### Primary User Story

An educator or developer wants to check whether a math word problem aligns to specific
academic standards. From the home page they open the Math Standards Alignment demo, choose a
grade and jurisdiction, pick one or more standards, paste a word problem, and run the
evaluation. The raw SDK result appears so they can inspect exactly what the SDK returns.

### Acceptance Scenarios

1. **Given** the Math Standards Alignment page, **When** it loads, **Then** the grade dropdown
   offers K–12 and the jurisdiction dropdown is populated from the SDK's supported
   jurisdictions (including Multi-State), defaulting to Multi-State.
2. **Given** a chosen grade and jurisdiction, **When** the selection settles, **Then** the
   standards for that grade/jurisdiction load into a searchable multi-select.
3. **Given** loaded standards, **When** the user changes grade or jurisdiction, **Then** the
   previous selection is cleared and the list reloads; a superseded in-flight response never
   overwrites the current list.
4. **Given** a word problem and at least one selected standard, **When** the user clicks
   Evaluate, **Then** the SDK runs and the raw JSON result renders in an output pane.
5. **Given** the Evaluate button, **When** no standard is selected or the problem is empty,
   **Then** the button is disabled.
6. **Given** a backend request, **When** input is invalid (bad grade/jurisdiction, empty or
   over-long problem, non-string standard codes), **Then** the API returns 400 with a clear
   message before any SDK/KG call.

### Edge Cases

- A grade/jurisdiction with more than 500 standards → API errors clearly instead of silently
  truncating.
- Invalid or unauthorized `PLATFORM_API_KEY` → KG 401 surfaced (body truncated) in the output.
- Missing keys at server start → the page's routes return 503 with a clear message; the rest
  of the demo still runs.
- Word problem at the 10,000-char limit → accepted; beyond it → rejected client- and
  server-side.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The page MUST offer a grade selector for K–12.
- **FR-002**: The page MUST offer a jurisdiction selector populated from the SDK's supported
  jurisdictions, including Multi-State, defaulting to Multi-State.
- **FR-003**: The page MUST show standards for the chosen grade + jurisdiction in a searchable
  multi-select allowing one or more selections.
- **FR-004**: Changing grade or jurisdiction MUST clear the current selection and reload the
  list, ignoring superseded responses.
- **FR-005**: The page MUST provide a multi-line word-problem input capped at 10,000 chars.
- **FR-006**: An Evaluate action MUST call the SDK's Math Standards Alignment evaluator with
  the word problem and selected standards and render the raw JSON result.
- **FR-007**: The backend MUST expose: supported jurisdictions; standards by grade +
  jurisdiction; and an evaluate endpoint, each validating input and returning `{ error }` on
  failure.
- **FR-008**: Because the published SDK exposes no public standards-listing helper, the
  backend MUST retrieve standards from the Knowledge Graph REST API directly, filtered to
  Mathematics and normalized standards, without silently truncating paginated results.
- **FR-009**: The evaluation and all Knowledge Graph calls MUST run server-side; keys MUST NOT
  reach the browser.
- **FR-010**: The feature MUST register itself in the scaffold's evaluator registry so it
  appears on the home page and routes at `/math-standards-alignment`.

### Key Entities

- **StandardOption**: `{ statementCode, description }` — one selectable standard.
- **Evaluate request**: `{ question, statementCodes[], jurisdiction }`.
- **Evaluate result**: the SDK's `evaluateItems` output (per-standard aligned/total counts and
  per-learning-component reasoning), passed through unchanged.

## Review & Acceptance Checklist

- [x] Requirements testable and unambiguous.
- [x] Grade is used only for standards lookup (not an evaluation input) — reflects the SDK.
- [x] SDK gap (no public standards helper) captured as a requirement + plan deviation.
- [x] Failure surfaces (validation, pagination, auth, missing keys) covered.

## Execution Status

- [x] Scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Implemented; standards lookup verified live; evaluate verified through the model layer
- [ ] Final real-key end-to-end evaluation run (pending user keys)
