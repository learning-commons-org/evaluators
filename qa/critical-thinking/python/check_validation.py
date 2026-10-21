"""Scenario D5: run every case in validation_cases.json and report PASS/FAIL.

Uses a dummy key, so no paid calls. Validation runs before the model is contacted; a case
that passes validation then fails with AuthenticationError, which counts as "accepted".

Usage (from qa/critical-thinking):
    ./run.sh py validate
"""

from __future__ import annotations

import copy
import json
import sys

from learning_commons_evaluators import CriticalThinkingEvaluator


def expand(value):  # noqa: ANN001, ANN201
    if isinstance(value, dict) and "$repeat" in value:
        char, n = value["$repeat"]
        return char * n
    if isinstance(value, dict):
        return {k: expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [expand(v) for v in value]
    return value


def main() -> int:
    with open(sys.argv[1], encoding="utf-8") as f:
        spec = json.load(f)

    evaluator = CriticalThinkingEvaluator(
        anthropic_api_key="sk-ant-qa-dummy-key", telemetry=False, max_retries=0
    )
    failures = 0
    for case in spec["cases"]:
        inputs = copy.deepcopy(spec["base"])
        inputs.update(expand(case.get("set", {})))
        for key in case.get("unset", []):
            inputs.pop(key, None)

        try:
            evaluator.evaluate_sync(**inputs)
            got_class, got_message = None, ""
        except Exception as error:  # noqa: BLE001
            got_class, got_message = type(error).__name__, str(error)

        expected = case["expect_error"]
        if expected is None:
            ok = got_class in (None, "AuthenticationError")
            detail = f"accepted (then {got_class})" if ok else f"{got_class}: {got_message}"
        else:
            ok = got_class == expected and got_message == case["message"]
            detail = f"{got_class}: {got_message}"
        failures += not ok
        print(f"{'PASS' if ok else 'FAIL'}  {case['id']}  {case['desc']}")
        if not ok:
            print(f"      expected: {expected}: {case.get('message', '(accepted)')}")
            print(f"      got:      {detail}")

    print(f"\n{len(spec['cases']) - failures}/{len(spec['cases'])} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
