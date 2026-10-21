"""Scenario D6: configuration and provider errors. Makes no billable calls.

1. No key                    -> ConfigurationError at construction, before any I/O
2. Invalid key               -> AuthenticationError, retryable False
3. Model that doesn't exist  -> ConfigurationError (needs ANTHROPIC_API_KEY; the call is refused)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from learning_commons_evaluators import CriticalThinkingEvaluator

INPUTS = json.loads((Path(__file__).parent.parent / "inputs" / "B-one-passage.json").read_text())
INPUTS.pop("_note", None)
failures = 0


def check(name: str, expected: str, fn) -> None:  # noqa: ANN001
    global failures
    try:
        fn()
        got, detail = None, "no error"
    except Exception as error:  # noqa: BLE001
        got, detail = type(error).__name__, str(error)
        retryable = getattr(error, "retryable", None)
        if retryable is not None:
            detail += f" (retryable={retryable})"
    ok = got == expected
    failures += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name}\n      expected {expected}; got {got}: {detail}")


check("1. no key", "ConfigurationError", lambda: CriticalThinkingEvaluator(telemetry=False))

check(
    "2. invalid key",
    "AuthenticationError",
    lambda: CriticalThinkingEvaluator(
        anthropic_api_key="sk-ant-qa-invalid", telemetry=False, max_retries=0
    ).evaluate_sync(**INPUTS),
)

key = os.environ.get("ANTHROPIC_API_KEY")
if not key:
    print("SKIP  3. unknown model (set ANTHROPIC_API_KEY in your shell or .env to run it)")
else:
    from learning_commons_evaluators import ModelOverride, Provider

    check(
        "3. unknown model",
        "ConfigurationError",
        lambda: CriticalThinkingEvaluator(
            anthropic_api_key=key,
            telemetry=False,
            max_retries=0,
            model_override=ModelOverride(provider=Provider.ANTHROPIC, model="claude-qa-does-not-exist"),
        ).evaluate_sync(**INPUTS),
    )

sys.exit(1 if failures else 0)
