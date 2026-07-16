# Plan: TypeScript SDK Demo App

## Structure

```
demos/typescript/
  spec.md / plan.md / tasks.md
  package.json            # single package: server + client deps, npm scripts
  .env.example            # ANTHROPIC_API_KEY, PLATFORM_API_KEY
  .gitignore              # .env, node_modules, dist
  vite.config.ts          # react plugin, proxy /api -> localhost:3001
  index.html
  server/
    index.ts              # Express app: 3 endpoints
    kg.ts                 # minimal KG REST helpers (framework UUID + standards by grade)
  src/
    main.tsx
    App.tsx               # all UI state + layout (small enough for one component)
    App.css               # minimal styling
```

One `package.json` (not a workspace) keeps the demo copy-pasteable. `npm run dev` runs
server and Vite concurrently; server runs via `tsx`.

## Dependencies

- Runtime: `@learning-commons/evaluators@^0.8.0`, peer deps `ai` + `@ai-sdk/anthropic`,
  `express`, `dotenv` (server-side env loading), `react`, `react-dom`, `react-select`.
- Dev: `vite`, `@vitejs/plugin-react`, `typescript`, `tsx`, `concurrently`, `@types/express`,
  `@types/react`, `@types/react-dom`.

## Key decisions

- **Backend replicates two KG REST calls** (framework UUID lookup with Multi-State
  short-circuit; standards by grade) in ~40 lines of plain `fetch` — mirrors
  `sdks/typescript/src/knowledge-graph/client.ts` behavior without importing internals.
- **Jurisdiction list comes from the SDK enum** on the server (`GET /api/jurisdictions`),
  proving the SDK helper exists rather than hardcoding the list in the frontend.
- **Evaluator instantiated once at server startup**; config errors (missing keys) fail fast
  with a clear message.
- **`evaluateItems`** (not `evaluate` in a loop) — one call covers 1 question × N standards.
- Errors from the SDK/KG are returned as `{ error: message }` with status 500 and shown
  verbatim in the output pane.

## Verification (definition of done)

- `npx tsc --noEmit` passes (this package has no test suite or linter of its own; the demo
  has no logic worth unit-testing — the SDK is the system under test).
- Manual end-to-end run with real keys: standards load for grade 3 / Multi-State, an
  evaluation of a sample word problem returns alignment JSON in the output pane.
