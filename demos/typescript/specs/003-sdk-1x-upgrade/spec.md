# Feature Specification: Upgrade to the 1.x Evaluators SDK

**Feature ID**: `003-sdk-1x-upgrade`
**Branch**: `003-sdk-1x-upgrade`
**Created**: 2026-09-23
**Status**: Implemented
**Input**: "Upgrade the demo to the latest evaluators TS SDK using what's documented, and land
the demo in its ideal, current state. Dependabot owns the version from here on."

## ⚡ Guidelines

- Builds on `001-demo-app-scaffold` and `002-math-standards-alignment`, which describe the demo
  as built on the 0.8 SDK. Those specs stay as the record of that build; this spec supersedes
  the parts of 002 that the 1.x SDK changed.
- Focus on WHAT changes for the user and WHY. The SDK's 0.8 → 1.x migration guide
  (`sdks/typescript/MIGRATION.md`) is the source for every breaking change handled here.
- No SDK version is written into the demo's docs or specs: Dependabot moves it, and a stated
  version would drift. `package.json` and the lockfile are the only record.

## User Scenarios & Testing *(mandatory)*

### Primary User Story

A developer evaluating the SDK opens the demo expecting it to show the SDK as it ships today.
The Math Standards Alignment page behaves as before (pick grade, jurisdiction, and standards;
enter a word problem; see the raw result), but it runs on the 1.x SDK, gets its standards
from the SDK instead of a hand-rolled Knowledge Graph call, and shows the 1.x result shape.

### Acceptance Scenarios

1. **Given** the demo's dependencies, **When** they are installed fresh, **Then** the install
   succeeds without `--legacy-peer-deps` or `--force`, with every required SDK peer (`ai`,
   `zod`) and the one provider adapter it uses (`@ai-sdk/anthropic`) declared by the demo.
2. **Given** a chosen grade and jurisdiction, **When** the standards load, **Then** they come
   from the SDK's standards catalog and include every standard for that grade, however many
   pages the Knowledge Graph returns.
3. **Given** a word problem and selected standards, **When** the user clicks Evaluate,
   **Then** the raw 1.x result renders, with its snake_case keys (e.g. `aligned_count`,
   `learning_components`) exactly as the SDK returns them.
4. **Given** the server starts, **When** `ANTHROPIC_API_KEY` or `LEARNING_COMMONS_API_KEY` is
   missing, **Then** the math routes return 503 naming both keys, and the rest of the demo runs.
5. **Given** the demo's CI gate, **When** it runs, **Then** typecheck and build pass.

### Edge Cases

- A grade/jurisdiction whose standards span several Knowledge Graph pages → all of them are
  listed. (002 errored above 500 rather than truncate; the SDK now paginates.)
- A Knowledge Graph standard with no statement code → omitted from the picker, since it cannot
  be selected or evaluated.
- Invalid or unauthorized `LEARNING_COMMONS_API_KEY` → the standards request fails and the
  SDK's error message is shown on the page; an evaluation that fails returns the SDK's
  per-standard `error` object inside the raw result.
- A developer with a `.env` from before this change → the missing-keys 503 names the renamed
  key, so the fix is visible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The demo MUST depend on the 1.x `@learning-commons/evaluators` SDK and declare
  its required peers (`ai`, and `zod`, which 1.x makes a consumer-declared peer) plus the one
  optional provider adapter it uses (`@ai-sdk/anthropic`).
- **FR-002**: The backend MUST list standards through the SDK's `StandardsCatalog`, scoped to
  Mathematics and the chosen jurisdiction, replacing the direct Knowledge Graph REST call that
  002 required (002 FR-008). This closes 002's first open follow-up.
- **FR-003**: The backend MUST call the evaluator with the 1.x input shape and credential
  names (`learningCommonsApiKey`; `statement_codes` on each item).
- **FR-004**: The evaluate endpoint MUST pass the SDK's result to the UI unchanged, as 002
  established.
- **FR-005**: The Learning Commons key MUST be read from `LEARNING_COMMONS_API_KEY`, the name
  the SDK's own documentation uses, replacing `PLATFORM_API_KEY`.
- **FR-006**: The README MUST describe the keys the demo now reads, and no demo doc or spec
  MAY state an SDK version.
- **FR-007**: The demo's own HTTP contract (routes, request fields, validation, 400/503
  behaviour) MUST be unchanged from 002, so the frontend needs no changes.

### Key Entities

- **StandardOption**: `{ statementCode, description }` — unchanged from 002; now mapped from
  the SDK's `AcademicStandard`.
- **Evaluate request**: `{ question, statementCodes[], jurisdiction }` — unchanged from 002.
  The server maps `statementCodes` onto the SDK's `statement_codes`.
- **Evaluate result**: the 1.x SDK's `evaluateItems` output, passed through unchanged.

## Out of Scope

- The other dependency bumps in Dependabot's grouped PR (TypeScript, Vite, and more). They
  arrive through Dependabot on their own; this spec covers only the SDK and the peers it
  requires.
- Renaming the demo's own request fields to snake_case. They are the demo's contract, not the
  SDK's, and renaming them would add churn to the frontend for no user-visible gain.

## Review & Acceptance Checklist

- [x] Every breaking change handled is traceable to the SDK's migration guide.
- [x] 002's open follow-ups checked against the 1.x SDK: both are addressed.
- [x] No SDK version appears in this spec.
- [ ] `StandardsCatalog` is exported but not yet in the SDK README; filing that docs gap is a
      follow-up (per the demo's CLAUDE.md, a gap found here is an SDK bug).

## Execution Status

- [x] Scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Implemented
- [x] Real-key end-to-end evaluation verified
