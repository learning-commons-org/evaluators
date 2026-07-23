# Tasks: Demo App Scaffold

**Feature ID**: `001-demo-app-scaffold`
**Input**: [spec.md](./spec.md), [plan.md](./plan.md)

## Format: `[ID] [P?] Description`

`[P]` = can run in parallel (different files, no dependency on an unfinished task).

## Phase 3.1: Setup

- [x] T001 Initialize `demos/typescript` package: `package.json` (deps: SDK + peers `ai@^7`,
      `@ai-sdk/anthropic@^4`, `express`, `dotenv`, `react`, `react-dom`, `react-router-dom`,
      `react-select`; scripts `dev`, `typecheck`).
- [x] T002 [P] Add `tsconfig.json` (bundler resolution, JSX, strict, `node` types).
- [x] T003 [P] Add `vite.config.ts` with React plugin and `/api` → `:3001` proxy.
- [x] T004 [P] Add `index.html` shell and `.gitignore` (ignore `.env`, `node_modules`, `dist`).
- [x] T005 [P] Add `.env.example` documenting required variables.

## Phase 3.2: Backend shell

- [x] T006 `server/index.ts`: Express app, JSON middleware, `GET /api/health`, and a single
      call site where evaluator features register routes.
- [x] T006a `server/index.ts`: graceful shutdown on `SIGINT`/`SIGTERM` (`server.close` +
      `closeAllConnections`) so tsx restarts don't hang or orphan the process (FR-010).

## Phase 3.3: Frontend shell

- [x] T007 `src/api.ts`: shared `fetchJson` (throws on non-OK with server `error`; readable
      message on non-JSON).
- [x] T008 `src/evaluators.tsx`: `EvaluatorDemo` type + registry array (single registration
      point consumed by home page and router).
- [x] T009 `src/pages/HomePage.tsx`: render registry entries as links; empty-state message.
- [x] T010 `src/App.tsx`: `<Routes>` with `/` → home and one route per registry entry.
- [x] T011 `src/main.tsx`: mount `<App>` inside `<BrowserRouter>`.
- [x] T012 [P] `src/App.css`: base layout, home list, and back-link styles.

## Phase 3.4: Docs

- [x] T013 [P] `README.md`: setup (install, `.env`) and run instructions.

## Phase 3.5: Verify

- [x] T014 `tsc --noEmit` clean.
- [x] T015 `vite build` clean.
- [x] T016 Smoke test: home page lists evaluators; `GET /api/health` returns `{status:"ok"}`.

## Dependencies

- T001 precedes everything (deps + scripts).
- T007–T008 precede T009–T011 (pages/router consume `fetchJson` and the registry).
- Verify phase (T014–T016) runs last.

## Parallel Example

```
# after T001, these are independent:
T002, T003, T004, T005 together
# after T008:
T009, T012 together
```
