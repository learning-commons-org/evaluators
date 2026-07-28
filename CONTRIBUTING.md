# Contributing

## One-time setup (per clone)

Enable the local check hooks (installs `pre-commit` + the harness deps and
wires up the git hook):

```shell
scripts/setup.sh
```

## Before committing

The pre-commit hook runs `python3 scripts/check.py --fix` automatically — it
strips notebook outputs and validates evaluator `config.json` / schemas /
fixtures against the shared contract. You can also run it by hand at any time:

```shell
python3 scripts/check.py --fix
```

If the hook ever gets in your way, `git commit --no-verify` bypasses it for one
commit — CI runs the same checks on every PR, so nothing unsafe can slip
through. See [`scripts/README.md`](./scripts/README.md) for the full check list
and how to add one.
