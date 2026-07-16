# Tasks: TypeScript SDK Demo App

1. [x] Scaffold `demos/typescript`: package.json, tsconfig, vite.config.ts, index.html,
       .gitignore, .env.example; install deps (published SDK + peers, express, react,
       react-select, tooling).
2. [x] Server: `server/kg.ts` — KG REST helpers (framework UUID with Multi-State
       short-circuit, standards by grade filtered to Mathematics/Standard).
3. [x] Server: `server/index.ts` — Express app with `GET /api/jurisdictions`,
       `GET /api/standards`, `POST /api/evaluate` using `MathStandardsAlignmentEvaluator`.
4. [x] Frontend: `src/App.tsx` + css — grade dropdown, jurisdiction dropdown, searchable
       standards multi-select, word-problem textarea, Evaluate button, JSON output pane,
       loading/error states.
5. [x] Verify: `tsc --noEmit` clean; vite build clean; server smoke test (jurisdictions,
       input validation); standards lookup verified live against KG (grade 5 / California →
       5.NF.A.1 …); evaluate path verified through model layer (auth-only failure on dummy
       key, no spec error). Pinned `ai@^7` to match `@ai-sdk/anthropic@4` (provider spec v4)
       — `ai@6` + anthropic@4 is a broken combo the SDK's loose `ai >=6.0.0` peer allows.
       **Remaining: user runs one real evaluation with both live keys.**
6. [x] README.md for the demo (setup, keys, run instructions).
