# Spec: TypeScript SDK Demo App — Math Standards Alignment

## Why

Demonstrate that the published `@learning-commons/evaluators` npm package works end-to-end
and show partners how to integrate it. First evaluator covered: **Math Standards Alignment**.
Other evaluators may be added later; the structure should not preclude that, but nothing
speculative is built now.

## What

A minimal web app at `demos/typescript/` consisting of a React (Vite) frontend and a small
Express backend. The backend is required because the SDK is Node-only (top-level `node:*`
imports on the evaluator path). The app consumes the **published npm package
`@learning-commons/evaluators@^0.8.0`**, not the workspace source.

### User flow

1. **Grade dropdown** — K, 1–12 (the SDK's supported grades for this evaluator).
2. **Jurisdiction dropdown** — populated from the SDK's `Jurisdiction` enum
   (`Object.values(Jurisdiction)`); includes all US states, Washington D.C., and
   `Multi-State` (Common Core). Default: `Multi-State`.
3. **Standards multi-select** — once grade and jurisdiction are chosen, the app fetches the
   math standards for that combination and shows them in a **searchable multi-select**
   (react-select). Each option shows `statementCode — description`. User picks one or more.
4. **Word problem textarea** — multi-line input for the question to evaluate
   (SDK limit: 10,000 chars).
5. **Evaluate button** — runs the evaluation and renders the **raw JSON result** in a
   `<pre>` output pane below. Shows a loading state while running and any error message
   verbatim on failure.

Changing grade or jurisdiction clears the current standards selection and reloads the list.

### Backend API (Express, port 3001)

| Endpoint | Behavior |
|---|---|
| `GET /api/jurisdictions` | Returns `Object.values(Jurisdiction)` from the SDK. |
| `GET /api/standards?grade=&jurisdiction=` | Returns `[{ statementCode, description }]` for math standards of that grade/jurisdiction. Because the published SDK does not export `KnowledgeGraphClient`, this endpoint calls the Knowledge Graph REST API directly (`https://api.learningcommons.org/knowledge-graph/v0`): resolve framework UUID via `/standards-frameworks?jurisdiction=…&academicSubject=Mathematics` (Multi-State short-circuits to the CCSS framework UUID `c6496676-d7cb-11e8-824f-0242ac160002`), then `/academic-standards?standardsFrameworkCaseIdentifierUUID=…&gradeLevel=…&normalizedStatementType=Standard&academicSubject=Mathematics&limit=500`. Auth: `x-api-key: PLATFORM_API_KEY`. |
| `POST /api/evaluate` | Body `{ question, statementCodes, jurisdiction }`. Runs `new MathStandardsAlignmentEvaluator({ anthropicApiKey, platformApiKey }).evaluateItems([{ question, statementCodes }], jurisdiction)` and returns the result JSON as-is. |

Grade is a UI/lookup concern only — the SDK's `evaluateItems` does not take a grade.

### Configuration

- `demos/typescript/.env` (gitignored): `ANTHROPIC_API_KEY`, `PLATFORM_API_KEY`.
- `demos/typescript/.env.example` checked in documenting both keys.
- Keys live server-side only; the browser never sees them.

### Non-goals

- No persistence, auth, styling framework, deployment config, or tests beyond what the
  demo needs to run. Plain readable code is the deliverable.
- No other evaluators (yet).
- No SDK changes. The missing public standards-listing helper is a known SDK gap tracked
  separately, not fixed here.

## Known SDK gap surfaced by this demo

The published package exposes no public API to list standards by grade + jurisdiction
(`KnowledgeGraphClient` is internal). The demo works around it via the KG REST API; a
future SDK release should export a helper so consumers don't have to.
