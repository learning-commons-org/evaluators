# Implementation Plan: Upgrade to the 1.x Evaluators SDK

**Feature ID**: `003-sdk-1x-upgrade`
**Date**: 2026-09-23
**Spec**: [spec.md](./spec.md)
**Depends on**: `001-demo-app-scaffold`, `002-math-standards-alignment`

## Summary

Move the demo onto the 1.x SDK: declare its peers, adopt the 1.x evaluator inputs and
credential name, and replace the hand-rolled Knowledge Graph helper with the SDK's
`StandardsCatalog`. The frontend and the demo's HTTP contract do not change.

## Technical Context

- **SDK surface**: `MathStandardsAlignmentEvaluator({ anthropicApiKey, learningCommonsApiKey })`
  and `.evaluateItems([{ question, statement_codes }], jurisdiction)`;
  `StandardsCatalog({ learningCommonsApiKey, academicSubject })` and
  `.listStandards(gradeLevel, { jurisdiction })`; `Jurisdiction` enum, unchanged.
- **Peers**: `ai`, `@ai-sdk/anthropic` (already declared), plus `zod`, now required. The
  migration guide's single install command is used so the peers move together.
- **Keys**: `ANTHROPIC_API_KEY`, `LEARNING_COMMONS_API_KEY`.
- **Everything else** inherited from 001 and 002.

## Constitution Check

- **Spec-driven**: spec → plan → tasks → code; 001 and 002 are left untouched. ✅
- **Scope discipline**: the SDK and the peers it requires only; other dependency bumps are
  Dependabot's. ✅
- **No version pins in docs**: the version lives in `package.json` and the lockfile only. ✅
- **Testing deviation**: as 001/002, verification is typecheck + build + live smoke. ✅

## Project Structure

### Documentation (this feature)

```
specs/003-sdk-1x-upgrade/
  spec.md  plan.md  tasks.md
```

### Source code (changed by this feature)

```
demos/typescript/
  package.json, package-lock.json   # SDK to 1.x; add zod
  server/
    math-standards-alignment.ts     # 1.x inputs + key; standards via StandardsCatalog
    kg.ts                           # deleted — superseded by StandardsCatalog
  .env.example                      # PLATFORM_API_KEY → LEARNING_COMMONS_API_KEY
  README.md                         # keys table
```

## Phase 0: Research

- **Migration guide, applied to this demo.** Of its sections, three reach this code: §0
  (upgrade SDK and peers together; `zod` becomes a declared peer), §6 (`platformApiKey` →
  `learningCommonsApiKey`), and §8 (`evaluateItems` items rename `statementCodes` →
  `statement_codes`; result keys become snake_case). The demo passes results through raw
  and names no result field, so §8's key changes need no code. Statement codes from the
  Knowledge Graph are already the bare dotted form §8 requires. §2 (result envelope) and §4
  (error classes) were checked and do not apply: `evaluateItems` returns no envelope, and the
  demo catches plain `Error` and forwards its message. One visible difference: standards
  lookup errors now carry the SDK's typed-error messages instead of `kg.ts`'s
  `Knowledge Graph request failed (<status>): <body>`.
- **002 follow-up 1 (standards-listing helper): addressed.** The 1.x SDK exports
  `StandardsCatalog` (changelog: #149). It is not in the SDK README, so it was confirmed from
  the published package's declarations and build: `listStandards` resolves the framework
  UUID (Multi-State → CCSS shortcut, otherwise by jurisdiction + subject), filters to
  normalized `Standard` statements for the subject and grade, and follows the cursor across
  every page. That is `server/kg.ts`'s behaviour plus pagination (and framework-UUID caching),
  and it is the same code path the evaluator uses to resolve codes. Grade values such as `K`
  pass through unchanged. `StandardsLookupOptions.jurisdiction` is typed `Jurisdiction`, so
  the already-validated string needs a cast, and the constructor throws `ConfigurationError`
  on an empty key, so the catalog is built only once both keys are known to be present.
- **002 follow-up 2 (peer range): addressed.** The 1.x SDK bounds `ai` to 7.x and
  `@ai-sdk/*` to 4.x, and declares `zod` 4 as a peer.
- **Node**: the 1.x engines field accepts the Node 22 line CI uses.
- **Dependabot's grouped PR** bumps the SDK alongside unrelated majors and fails typecheck.
  Two of its errors are this spec's (`platformApiKey`, `statementCodes`); the third,
  `Cannot find module ... side-effect import of './App.css'`, is not an SDK error and
  appears with that PR's TypeScript major bump; it is not this spec's concern.

## Phase 1: Design & Contracts

- `GET /api/jurisdictions`, `GET /api/standards`, `POST /api/evaluate`: routes, validation,
  and error shapes unchanged from 002.
- `/api/standards` calls `catalog.listStandards(grade, { jurisdiction })` on a catalog built
  once with `academicSubject: 'Mathematics'`, drops entries with no statement code, and maps
  to `StandardOption` with `description ?? ''`.
- `/api/evaluate` maps the request's `statementCodes` to `statement_codes`.
- Missing keys → all three routes return 503, the message naming `ANTHROPIC_API_KEY` and
  `LEARNING_COMMONS_API_KEY`.

## Phase 2: Task Planning Approach

Dependencies → backend → docs → verify. See [tasks.md](./tasks.md).

## Complexity Tracking

| Decision | Why | Simpler alternative rejected |
|---|---|---|
| Adopt `StandardsCatalog`, delete `kg.ts` | Same behaviour plus pagination, on the SDK's own resolution path; the demo shows the SDK rather than working around it | Keep `kg.ts` — keeps a workaround for a gap that no longer exists |
| Rename the env var to `LEARNING_COMMONS_API_KEY` | Matches the SDK docs and the 1.x option name, so the demo reads like the SDK's own examples | Keep `PLATFORM_API_KEY` — no churn for existing `.env` files, but names a concept 1.x removed |
| Keep the demo's `statementCodes` request field | It is the demo's contract; the frontend stays untouched | Snake_case it to mirror the SDK — frontend churn, no user-visible gain |

## Open Follow-ups (SDK, out of scope here)

- Document `StandardsCatalog` in the SDK README; it is exported but undocumented.
