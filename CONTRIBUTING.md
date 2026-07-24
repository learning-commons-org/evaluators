# Contributing

This repository is **public but not open to external contributions.** It's the
published export of evaluators developed internally at Learning Commons, so we
don't accept outside pull requests. For questions or feedback, please
[open an issue](https://github.com/learning-commons-org/evaluators/issues) or
reach us at [support@learningcommons.org](mailto:support@learningcommons.org).

## For Learning Commons contributors

### One-time setup (per clone)

Enable the local check hooks:

```shell
scripts/setup.sh
```

(equivalently: `pip install pre-commit && pre-commit install`)

### Before committing

The pre-commit hook runs `python scripts/check.py --fix` automatically — it
strips notebook outputs and validates evaluator `config.json` / schemas /
fixtures against the shared contract. You can also run it by hand at any time:

```shell
python scripts/check.py --fix
```

If the hook ever gets in your way, `git commit --no-verify` bypasses it for one
commit — CI runs the same checks on every PR, so nothing unsafe can slip
through. See [`scripts/README.md`](./scripts/README.md) for the full check list
and how to add one.
