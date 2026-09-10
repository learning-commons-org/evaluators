# demos/typescript

Vite + React + Express demo consuming the **published** `@learning-commons/evaluators` package — not a workspace link. It exercises the SDK the way an integrator would, so treat a gap found here as an SDK bug worth filing.

## Verify

```shell
npm run typecheck   # the only check; there is no test suite
npm run dev         # Express server + Vite together
```

## Spec-driven

This is the one place in the repo that uses spec-driven development. Features live in `specs/<nnn>-<slug>/` and progress spec → plan → tasks → implementation. Add a spec before building a feature here.
