# Tasks: Math Standards Alignment Evaluator Page

**Feature ID**: `002-math-standards-alignment`
**Input**: [spec.md](./spec.md), [plan.md](./plan.md)
**Prerequisite**: `001-demo-app-scaffold` complete

## Format: `[ID] [P?] Description`

`[P]` = can run in parallel (different files, no dependency on an unfinished task).

## Phase 3.1: Backend

- [x] T001 `server/kg.ts`: Knowledge Graph REST helpers — resolve framework UUID
      (Multi-State → CCSS shortcut) and list Mathematics/Standard standards by grade; guard
      against silent pagination truncation; truncate error bodies.
- [x] T002 `server/math-standards-alignment.ts`: `registerMathStandardsAlignment(app)`
      exposing `GET /api/jurisdictions`, `GET /api/standards`, `POST /api/evaluate`; validate
      inputs (grade, jurisdiction, question length, statementCodes) → 400; construct the SDK
      evaluator; degrade to 503 when keys are missing.
- [x] T003 Register the feature in the scaffold: call `registerMathStandardsAlignment(app)`
      in `server/index.ts`.

## Phase 3.2: Frontend

- [x] T004 `src/pages/MathStandardsAlignmentPage.tsx`: grade + jurisdiction selectors,
      `react-select` searchable standards multi-select, word-problem textarea (≤10,000),
      Evaluate button, JSON output pane, error/loading states, stale-response guard, back link.
- [x] T005 `src/evaluators.tsx`: add the registry entry (`/math-standards-alignment`, title,
      description, page element) so the home page and router expose it.

## Phase 3.3: Docs

- [x] T006 [P] Update `README.md` to list this evaluator and its route.

## Phase 3.4: Verify

- [x] T007 `tsc --noEmit` clean; `vite build` clean.
- [x] T008 Live smoke: `/api/standards` returns real standards (e.g. grade 3 / Multi-State →
      `3.MD.C.7.d`); input validation returns 400; evaluate reaches the model layer.
- [ ] T009 Final real-key end-to-end evaluation run (pending user keys).

## Dependencies

- T001 precedes T002 (router calls `listStandards`).
- T002 precedes T003 (scaffold registers the router).
- T004 depends on the scaffold's `fetchJson`; T005 depends on T004 (imports the page).
- Verify (T007–T009) runs last.

## Parallel Example

```
# T006 (docs) is independent once the code lands:
T006 alongside T007
```
