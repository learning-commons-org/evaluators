# Implementation Plan: Math Standards Alignment Evaluator Page

**Feature ID**: `002-math-standards-alignment`
**Date**: 2026-07-16
**Spec**: [spec.md](./spec.md)
**Depends on**: `001-demo-app-scaffold`

## Summary

Add a Math Standards Alignment demo page to the scaffold: a form (grade, jurisdiction,
searchable standards multi-select, word problem) that calls three backend routes — supported
jurisdictions, standards by grade/jurisdiction, and evaluate — with the SDK and a direct
Knowledge Graph REST call doing the work server-side.

## Technical Context

- **SDK surface**: `MathStandardsAlignmentEvaluator.evaluateItems([{ question, statementCodes }],
  jurisdiction)`; `Jurisdiction` enum for the dropdown.
- **Keys**: `ANTHROPIC_API_KEY` (default model is Claude), `PLATFORM_API_KEY` (Knowledge Graph).
- **Knowledge Graph**: `https://api.learningcommons.org/knowledge-graph/v0`, `x-api-key` auth.
- **Frontend**: `react-select` for the searchable multi-select.
- **Everything else** inherited from the scaffold's Technical Context.

## Constitution Check

- **Spec-driven**: spec → plan → tasks → code. ✅
- **Scope discipline**: only Math Standards Alignment; no other evaluators. ✅
- **Testing deviation**: same as scaffold — verification is typecheck + build + live smoke,
  not automated tests (demo of the published SDK). ✅

## Project Structure

### Documentation (this feature)

```
specs/002-math-standards-alignment/
  spec.md  plan.md  tasks.md
```

### Source code (added by this feature)

```
demos/typescript/
  server/
    math-standards-alignment.ts   # registerMathStandardsAlignment(app): the 3 routes
    kg.ts                         # Knowledge Graph REST helpers (standards listing)
  src/
    pages/
      MathStandardsAlignmentPage.tsx  # the form + output pane
    evaluators.tsx                # registry entry for this page (edit: add one entry)
```

## Phase 0: Research

- **No public standards-listing helper.** The SDK's `KnowledgeGraphClient` is internal, so
  standards for the picker are fetched via the KG REST API directly, replicating the SDK's
  framework-UUID lookup (Multi-State → CCSS framework UUID) and Mathematics/Standard filter.
- **AI SDK version coupling.** The SDK is built against `ai@7` / `@ai-sdk/provider@4` (spec
  v4). Pairing `ai@6` with `@ai-sdk/anthropic@4` throws "Unsupported model version"; the
  scaffold pins `ai@^7`.
- **Grade is not an evaluation input.** It only scopes the standards lookup; `evaluateItems`
  takes the question + codes + jurisdiction.

## Phase 1: Design & Contracts

- `GET /api/jurisdictions` → `string[]` from `Object.values(Jurisdiction)`.
- `GET /api/standards?grade&jurisdiction` → `StandardOption[]`; 400 on bad grade/jurisdiction;
  throws (→500) rather than truncating a paginated KG result.
- `POST /api/evaluate` `{ question, statementCodes, jurisdiction }` → SDK result; 400 unless
  the problem is non-empty and ≤10,000 chars, `statementCodes` is a non-empty string array,
  and jurisdiction is valid.
- If keys are missing at boot, all three routes return 503 (feature degrades, scaffold runs).
- Frontend reloads standards on grade/jurisdiction change with an ignore-flag guard against
  stale responses.

## Phase 2: Task Planning Approach

Tasks: backend KG helper → backend feature router → frontend page → registry wiring → verify.
See [tasks.md](./tasks.md).

## Complexity Tracking

| Decision | Why | Simpler alternative rejected |
|---|---|---|
| Direct KG REST call in `kg.ts` | SDK exposes no public standards-listing helper | Deep-import SDK internals — fragile, unpublished API |
| Routes 503 when keys absent | Keep scaffold + other evaluators running | Hard exit at boot — breaks the whole demo for one feature |
| Pass raw SDK JSON to the UI | Demo's purpose is to show exactly what the SDK returns | Reshape output — hides the real contract |

## Open Follow-ups (SDK, out of scope here)

- Export a public `getStandardsByGrade`-style helper so demos need no direct KG call.
- Tighten the SDK peer range from `ai >=6.0.0` to `ai >=7`.
