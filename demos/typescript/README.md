# TypeScript SDK Demo — Math Standards Alignment

Minimal web app demonstrating the published
[`@learning-commons/evaluators`](https://www.npmjs.com/package/@learning-commons/evaluators)
SDK: pick a grade, jurisdiction, and standards, enter a math word problem, and view the
evaluator's alignment result. React (Vite) frontend + a small Express backend that runs the
Node-only SDK.

## Setup

```bash
npm install
cp .env.example .env    # then fill in both keys
```

| Key | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | LLM calls (the evaluator's default model is Claude) |
| `PLATFORM_API_KEY`  | Learning Commons Knowledge Graph (standards lookup) |

## Run

```bash
npm run dev
```

Open http://localhost:5173 (the Vite dev server proxies `/api` to the backend on `:3001`).
