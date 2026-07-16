# Feature Specification: Demo App Scaffold

**Feature ID**: `001-demo-app-scaffold`
**Branch**: `001-demo-app-scaffold`
**Created**: 2026-07-16
**Status**: Implemented
**Input**: "Implement a TS SDK demo app — the empty demo app shell, ready to go, that
future evaluator demos plug into."

## ⚡ Guidelines

- Describes the reusable shell only. No evaluator-specific behavior lives here — that
  arrives as separate features (`002-…`, `003-…`).
- Focus on WHAT the scaffold provides and WHY, not implementation detail.

## User Scenarios & Testing *(mandatory)*

### Primary User Story

A developer wants to see the `@learning-commons/evaluators` SDK working through a browser.
They clone the repo, install, provide keys, and start the app. A home page greets them and
lists the available evaluator demos; selecting one opens that evaluator's page. New evaluator
demos can be added later without disturbing existing ones.

### Acceptance Scenarios

1. **Given** a fresh checkout with dependencies installed, **When** the developer runs the
   dev command and opens the app root, **Then** a home page renders listing the registered
   evaluator demos as navigable links.
2. **Given** the home page, **When** the developer clicks an evaluator link, **Then** the app
   navigates client-side to that evaluator's page without a full reload.
3. **Given** an evaluator page, **When** the developer follows the "all evaluators" link,
   **Then** they return to the home page.
4. **Given** the backend is not running, **When** a page calls the API, **Then** the user sees
   a clear "is the backend running?" message rather than an opaque parse error.
5. **Given** a new evaluator demo is added at its single registration point, **When** the app
   rebuilds, **Then** the home page and router expose it with no other edits.

### Edge Cases

- No evaluator demos registered → home page states that none are registered yet.
- Backend down or non-JSON response → surfaced as a readable error.
- Deep-linking directly to an evaluator route in dev → served by the SPA (dev-server
  fallback), not a 404.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The frontend MUST be a single-page React app (built with Vite) using
  client-side routing.
- **FR-002**: The app MUST present a home page at `/` that lists registered evaluator demos,
  each linking to its page.
- **FR-003**: Evaluator demos MUST be declared in one registration point that both the home
  page and the router consume, so adding one requires no changes to existing pages.
- **FR-004**: Each evaluator page MUST provide a way back to the home page.
- **FR-005**: The backend MUST be a separate Express server (the SDK is Node-only) and expose
  a health-check endpoint.
- **FR-006**: The dev setup MUST proxy the frontend's `/api` calls to the backend so the
  browser stays same-origin and never receives API keys.
- **FR-007**: The backend MUST load configuration from a `.env` file, with a checked-in
  `.env.example` documenting the variables.
- **FR-008**: The scaffold MUST run even when evaluator-specific secrets are absent; a feature
  lacking its keys degrades to a clear error on its own routes only.
- **FR-009**: Each evaluator feature MUST register its API routes at a single call site in the
  server without modifying the scaffold's core.
- **FR-010**: The backend MUST shut down promptly on `SIGINT`/`SIGTERM` (close the listener and
  drop keep-alive connections) so dev-server restarts don't hang or orphan the process.

### Key Entities

- **EvaluatorDemo**: a registry entry describing one demo — `path`, `title`, `description`,
  and the page element to render.

## Review & Acceptance Checklist

- [x] No implementation detail leaks into requirements (framework names appear only as
      established project constraints).
- [x] Requirements are testable and unambiguous.
- [x] Scope is the shell only; evaluator behavior deferred to later features.
- [x] Acceptance scenarios cover navigation, extensibility, and failure surfaces.

## Execution Status

- [x] Scenarios defined
- [x] Requirements generated
- [x] Entities identified
- [x] Implemented and verified (typecheck, build, home/route smoke test)
