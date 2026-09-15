# Evaluators

Learning-science-backed LLM-as-a-judge evaluators, shipped three ways: prompt + schema bundles under `evals/`, and TypeScript and Python SDKs under `sdks/`.

## Layout

| Path                | What it is                                                        |
| ------------------- | ----------------------------------------------------------------- |
| `evals/`            | Evaluator definitions — prompts, schemas, fixtures, notebooks     |
| `sdks/typescript/`  | `@learning-commons/evaluators` npm package                        |
| `sdks/python/`      | `learning-commons-evaluators` PyPI package                        |
| `sdks/settings/`    | Per-evaluator TOML shared by both SDKs (source of truth)          |
| `datasets/`         | Expert-annotated datasets behind the evaluators                   |
| `demos/typescript/` | Vite + React + Express demo of the published TS SDK               |
| `scripts/`          | Repo check harness — see [`scripts/README.md`](scripts/README.md) |

## Before committing

```shell
python3 scripts/check.py --fix   # same harness CI runs; --list to see the checks
```

`scripts/setup.sh` (once per clone) wires this up as a pre-commit hook. See [`CONTRIBUTING.md`](CONTRIBUTING.md).

Per-workspace suites are separate and not yet delegated to by the harness:

| Workspace           | Verify with                                              |
| ------------------- | -------------------------------------------------------- |
| `sdks/typescript/`  | `npm run lint && npm run typecheck && npm run test:unit` |
| `sdks/python/`      | `make verify`                                            |
| `demos/typescript/` | `npm run typecheck`                                      |

## Conventions

- **Conventional commits are enforced** on PR titles and commits by `.github/workflows/conventional-commits.yml`.
- **Releases are automated by release-please.** Never hand-edit a version or `CHANGELOG.md` in `evals/prompts`, `sdks/python`, or `sdks/typescript`.
- **Generated files are never hand-edited.** `.gitattributes` lists them all, each with the command that regenerates it.
