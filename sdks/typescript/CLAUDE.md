# sdks/typescript

`@learning-commons/evaluators`. Node `^20.19.0 || >=22.12.0`; CI tests on 20.19.0, 22, and 24.

## Verify

```shell
npm run lint && npm run typecheck && npm run test:unit
```

Integration tests need real API keys and are opt-in: `npm run test:integration` (see [`tests/README.md`](tests/README.md)). `npm run test:ci` is the full gate — unit plus integration against `dist/`.

## Two published entry points

- `.` → `src/index.ts` — the evaluators
- `./batch` → `src/batch/` — also the `evaluators-batch` CLI bin

`batch/package.json` is a resolver stub for tools that ignore `exports`; it is not a workspace. Changing either entry point means re-running `npm run verify:dist` and `npm run verify:package`.

## Generated code

- `src/schemas/**` — from `sdks/settings/`; `npm run generate:schemas`. CI runs `generate:schemas:check` and fails on drift.
- `src/knowledge-graph/kg-api.d.ts` — from the published KG OpenAPI spec; `npm run generate:kg-types`.
- `src/telemetry/types.generated.ts` — the telemetry event's types and wire serializer, from `evals/telemetry/event.schema.json`; `python3 scripts/generate_telemetry_schema.py` from the repo root. The repo-checks `telemetry-schema` check fails on drift.

`sdks/settings/<evaluator>/settings.toml` is the source of truth shared with the Python SDK — change it there, then regenerate on both sides.

`CHANGELOG.md` and the `package.json` version are release-please managed.
