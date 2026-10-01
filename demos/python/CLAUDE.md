# demos/python

FastAPI + Jinja demo of the `learning-commons-evaluators` Python SDK, installed as a package — never imported from `sdks/python/src`. It exercises the SDK the way an integrator would, so treat a gap found here as an SDK or README bug worth filing.

## Verify

```shell
ruff check . && ruff format --check . && pytest -q
uvicorn app:app --reload   # http://localhost:8000
```

## Spec-driven

Features live in `specs/<nnn>-<slug>/` and progress spec → plan → tasks → implementation. Add a spec before building a feature here.
