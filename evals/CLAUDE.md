# evals/

Each evaluator is a self-contained directory: `evals/<domain>/<skill-modality>/<evaluator>/` — e.g. `student-facing-text/ela-reading/sentence-structure/`.

## The evaluator contract

Every evaluator directory holds:

| File                     | Role                                                    |
| ------------------------ | ------------------------------------------------------- |
| `config.json`            | The manifest — declares steps, prompts, and schema refs |
| `input_schema.json`      | JSON Schema for the evaluator's input                   |
| `output_schema.json`     | JSON Schema for its output                              |
| `fixtures.json`          | Cases bound to those two schemas                        |
| `example_notebook.ipynb` | Runnable example                                        |
| prompt `.txt` files      | Named by `config.json`, not by convention               |

`config.json` is validated against `_schemas/config.schema.json` (which it references via its own `$schema`). Prompt filenames vary per evaluator — single-step ones use `system.txt` / `user.txt`, multi-step ones name their own.

## Editing a prompt requires updating its hash

`config.json` pins each prompt file by `sha256`. The `eval-config` check fails on drift and **does not auto-fix it** — the hash is a deliberate tripwire, so recompute it by hand when you change prompt text:

```shell
shasum -a 256 evals/<domain>/<skill-modality>/<evaluator>/system.txt
```

The same check verifies that placeholders in `config.json` and `{vars}` in the template stay in sync, and that system prompts carry no placeholders.

## Other things the harness enforces

- Notebook outputs are stripped on commit — don't commit executed notebooks.
- Notebooks must load config and prompts from disk, never inline copies.
- New imports need a matching entry in `requirements.txt` (checked both ways).
- `stable_id` / `id` / `id_history` values are never reused across evaluators.

`evals/prompts/CHANGELOG.md` is release-please managed — don't hand-edit it.

Run `make install` for the notebook environment; see [`README.md`](README.md).
