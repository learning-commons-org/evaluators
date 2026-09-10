# sdks/python

`learning-commons-evaluators`. Requires Python >= 3.10; CI tests 3.10–3.13.

## Verify

```shell
make verify   # what CI runs: build check, lint, format, typecheck, pip check, tests
make help     # every target, with the common workflows spelled out
```

## Generated code

`src/learning_commons_evaluators/settings/` holds two generated artifacts:

- `_generated_*_settings.py` — `make generate-settings`
- `contracts.toml` — a bundled copy, `make sync-settings`

Both derive from `sdks/settings/`, which is shared with the TypeScript SDK.
After editing any TOML there: `make build` (does both), then `make verify`.
`make check-build` is the CI guard that catches a stale checkout.

Mypy targets 3.10 even when you run it on a newer interpreter.

`CHANGELOG.md` and the `pyproject.toml` version are release-please managed.
