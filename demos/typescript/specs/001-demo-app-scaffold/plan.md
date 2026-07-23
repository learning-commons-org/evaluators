# Implementation Plan: Demo App Scaffold

**Feature ID**: `001-demo-app-scaffold`
**Date**: 2026-07-16
**Spec**: [spec.md](./spec.md)

## Summary

Stand up a minimal, extensible Vite + React + Express shell for SDK demos: a home page that
lists evaluator demos from a single registry, client-side routing to each demo page, and an
Express backend that loads `.env`, exposes a health check, and lets each evaluator feature
register its own routes at one call site.

## Technical Context

- **Language/Version**: TypeScript 5.8, Node `>=20.19.0`
- **Frontend**: React 19, Vite 7, `react-router-dom` 7
- **Backend**: Express 5, `dotenv`, run with `tsx`
- **SDK**: `@learning-commons/evaluators` (peers `ai@^7`, `@ai-sdk/anthropic@^4`)
- **Target platform**: local dev (browser + Node backend)
- **Project type**: web (frontend + backend in one package)
- **Testing**: manual verification (typecheck, build, smoke) — see Constitution Check
- **Constraints**: SDK is Node-only, so all SDK usage is server-side; keys never reach the
  browser

## Constitution Check

- **Spec-driven**: spec precedes this plan precedes tasks precedes code. ✅
- **Scope discipline**: scaffold only; no evaluator logic. ✅
- **Definition of Done deviation**: the global standard requires automated tests + lint. This
  package ships no test/lint tooling: it is a demo whose purpose is to exercise the *published
  SDK* (the system under test), and the scaffold has no business logic worth unit-testing.
  Done is defined here as `tsc --noEmit` clean, `vite build` clean, and a manual smoke test.
  Recorded as an intentional deviation.

## Project Structure

### Documentation (this feature)

```
specs/001-demo-app-scaffold/
  spec.md  plan.md  tasks.md
```

### Source code (added by this feature)

```
demos/typescript/
  package.json  tsconfig.json  vite.config.ts  index.html
  .env.example  .gitignore  README.md
  server/
    index.ts          # express app, health check, feature route registration
  src/
    main.tsx          # BrowserRouter mount
    App.tsx           # <Routes> built from the evaluator registry + home
    api.ts            # shared fetchJson helper
    evaluators.tsx    # EvaluatorDemo type + registry (starts describing 002)
    App.css
    pages/
      HomePage.tsx     # lists registry entries
```

## Phase 0: Research

- **Node-only SDK** → confirmed top-level `node:*` imports on the eval path; backend required.
- **Routing**: `react-router-dom` chosen as the minimal standard for multi-page SPA; a
  registry-driven `<Routes>` keeps feature addition to one entry.
- **Dev proxy**: Vite `server.proxy` forwards `/api` → `:3001`, keeping same-origin and hiding
  keys from the browser.

## Phase 1: Design & Contracts

- **Registry contract** (`EvaluatorDemo`): `{ path, title, description, element }`. Home page
  maps it to links; `App.tsx` maps it to routes.
- **Backend contract**: `GET /api/health` → `{ status: 'ok' }`. Feature routers are mounted
  via `register<Feature>(app)` calls in `server/index.ts`.
- **Error contract**: API errors return `{ error: string }`; the shared `fetchJson` surfaces
  `error` or a "backend running?" message on non-JSON.

## Phase 2: Task Planning Approach

Tasks derive from the structure above: initialize the package and tooling, build the backend
shell, build the routed frontend shell with the registry and home page, then verify. See
[tasks.md](./tasks.md).

## Complexity Tracking

| Decision | Why | Simpler alternative rejected |
|---|---|---|
| Separate Express backend | SDK is Node-only | Browser-only app — impossible with this SDK |
| `react-router-dom` | Multi-page requirement (home + per-evaluator) | Single page — fails FR-002/FR-003 |
| No automated tests | Demo of published SDK; no local business logic | Test suite — disproportionate for a demo |
