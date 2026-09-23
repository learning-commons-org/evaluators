# Tasks: Upgrade to the 1.x Evaluators SDK

**Feature ID**: `003-sdk-1x-upgrade`
**Input**: [spec.md](./spec.md), [plan.md](./plan.md)
**Prerequisite**: `002-math-standards-alignment` complete

## Format: `[ID] [P?] [USER?] Description`

`[P]` = can run in parallel (different files, no dependency on an unfinished task).
`[USER]` = the implementer cannot do this step; stop and ask the user, and wait for them to
confirm it is done before continuing past it.

Run every command from `demos/typescript/`. Run `nvm use` once per shell before the first
`npm`/`npx` command. Do not edit anything under `specs/001-*` or `specs/002-*`. Do not write an
SDK version into any doc or spec.

## Phase 3.1: Dependencies

- [ ] T001 Upgrade the SDK and its peers together using the install command in
      `../../sdks/typescript/MIGRATION.md` §0, keeping only the one adapter the demo uses
      (`@ai-sdk/anthropic`) and dropping `@ai-sdk/google` and `@ai-sdk/openai` from it.
      Do not pass `--legacy-peer-deps` or `--force`, and do not run `npm audit fix` (the
      install reports a pre-existing advisory that is out of scope).
      **Pass**: exit code 0, no `ERESOLVE` in the output. In `package.json`, the
      `@learning-commons/evaluators` range moves to 1.x, `zod` is added, and the `ai` and
      `@ai-sdk/anthropic` ranges may rise; no other `dependencies` or `devDependencies` entry
      changes. `package-lock.json` is updated.

## Phase 3.2: Backend

- [ ] T002 `server/math-standards-alignment.ts` — make exactly these edits:
      - Delete the line `import { listStandards } from './kg.js';` and add `StandardsCatalog`
        to the existing `@learning-commons/evaluators` import.
      - Replace every `PLATFORM_API_KEY` with `LEARNING_COMMONS_API_KEY` (the destructure,
        the `if`, and the 503 message). The message becomes exactly
        `'Math Standards Alignment is disabled: set ANTHROPIC_API_KEY and LEARNING_COMMONS_API_KEY in .env'`.
      - In the `MathStandardsAlignmentEvaluator` constructor, rename `platformApiKey:` to
        `learningCommonsApiKey:`.
      - Directly after the evaluator is constructed — inside the keys-present path, never
        before the missing-key `return` (the constructor throws on an empty key) — add:
        `const catalog = new StandardsCatalog({ learningCommonsApiKey: LEARNING_COMMONS_API_KEY, academicSubject: 'Mathematics' });`
      - In the `/api/standards` handler, replace
        `res.json(await listStandards(grade, jurisdiction, PLATFORM_API_KEY));` with:
        ```ts
        const standards = await catalog.listStandards(grade, { jurisdiction: jurisdiction as Jurisdiction });
        res.json(
          standards.flatMap((s) =>
            s.statementCode != null ? [{ statementCode: s.statementCode, description: s.description ?? '' }] : [],
          ),
        );
        ```
      - In the `/api/evaluate` handler, change `[{ question, statementCodes }]` to
        `[{ question, statement_codes: statementCodes }]`.
      - Change nothing else: validation, status codes, and try/catch blocks stay as they are.
        Do not declare a `StandardOption` type.
- [ ] T003 Delete `server/kg.ts`.

## Phase 3.3: Docs

- [x] T004 [USER] In `.env.example`, rename `PLATFORM_API_KEY` to `LEARNING_COMMONS_API_KEY`,
      and make sure `.env` sets `LEARNING_COMMONS_API_KEY` (it may be shared with other
      checkouts, so the user adds the key there rather than renaming it). The implementer
      cannot read or write `.env*` files. Ask the user to do this, and wait for confirmation
      before T007.
- [ ] T005 [P] `README.md`: in the keys table, replace the row
      `` | `PLATFORM_API_KEY`  | Learning Commons Knowledge Graph (standards lookup) | `` with
      `` | `LEARNING_COMMONS_API_KEY` | Learning Commons API (standards lookup and the evaluator's standards resolution) | ``.
      Change nothing else in the README, and add no SDK version.

## Phase 3.4: Verify

- [ ] T006 Run `npm run typecheck`, then `npm run build`.
      **Pass**: both exit 0; `tsc` prints no errors; vite's output ends with a `✓ built in`
      line. Then run
      `grep -rnE "kg\.js|kg\.ts|listStandards\(grade, jurisdiction|PLATFORM_API_KEY|platformApiKey" server src README.md`
      — **pass** is no output.
- [ ] T007 Live smoke (requires T004 confirmed). Start only the API server in the background
      with `npx tsx server/index.ts`; its log must show
      `API server listening on http://localhost:3001` and no `disabled` warning. Then:
      - `curl -s 'localhost:3001/api/standards?grade=3&jurisdiction=Multi-State'` → a JSON
        array containing an entry with `"statementCode":"3.MD.C.7.d"`.
      - `curl -s 'localhost:3001/api/standards?grade=K&jurisdiction=Texas'` → a non-empty JSON
        array.
      - `curl -s -o /dev/null -w '%{http_code}' 'localhost:3001/api/standards?grade=13&jurisdiction=Multi-State'`
        → `400`.
      Stop the server with `lsof -ti:3001 | xargs kill`. Then check the missing-key path by
      starting it with the keys set to empty (empty, not unset — otherwise `.env` reloads
      them): `ANTHROPIC_API_KEY= LEARNING_COMMONS_API_KEY= npx tsx server/index.ts` in the
      background, and run
      `curl -s -w ' %{http_code}' 'localhost:3001/api/standards?grade=3&jurisdiction=Multi-State'`
      → a body naming both `ANTHROPIC_API_KEY` and `LEARNING_COMMONS_API_KEY`, followed by
      `503`. Stop the server the same way.
- [ ] T008 [USER] Real-key end-to-end: with `npm run dev` running, open
      http://localhost:5173, go to Math Standards Alignment, and pick grade, jurisdiction,
      and standards, enter a word problem, and click Evaluate. **Pass**: the output pane shows
      the raw result with 1.x snake_case keys (`statement_code`, `learning_components`,
      `aligned_count`, `total_count`). This makes a paid model call.
- [ ] T009 Close out: tick the completed tasks in this file. In `spec.md`, set **Status** to
      `Implemented` and tick "Implemented" under Execution Status. Leave the real-key box for
      the user to tick after T008.

## Dependencies

- T001 precedes T002 (the 1.x types must be installed to compile).
- T002 precedes T003 (the router stops importing `kg.ts`).
- T004 must be confirmed by the user before T007. T005 is independent of the code.
- Verify (T006–T008) runs after T001–T005; T009 runs last.

## Parallel Example

```
# The README edit is independent once the dependency lands:
T005 alongside T002
```
