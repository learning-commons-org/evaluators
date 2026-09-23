# TypeScript SDK Demo

Minimal web app demonstrating the published
[`@learning-commons/evaluators`](https://www.npmjs.com/package/@learning-commons/evaluators)
SDK. The home page lists the available evaluator demos; each is its own page. React (Vite)
frontend + a small Express backend that runs the Node-only SDK.

Evaluators:

- **Math Standards Alignment** (`/math-standards-alignment`) — pick a grade, jurisdiction, and
  standards, enter a math word problem, and view the evaluator's alignment result.

## Setup

```bash
npm install
cp .env.example .env    # then fill in both keys
```

| Key | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | LLM calls (the evaluator's default model is Claude) |
| `LEARNING_COMMONS_API_KEY` | Learning Commons API (standards lookup and the evaluator's standards resolution) |

## Run

```bash
npm run dev
```

Open http://localhost:5173 to reach the home page (the Vite dev server proxies `/api` to the
backend on `:3001`), then pick an evaluator.
