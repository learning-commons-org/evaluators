"""Scenario D7: three concurrent evaluations, then evaluate_sync inside a running loop.

    ./run.sh py async inputs/B-one-passage.json      (three paid calls)
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time

from learning_commons_evaluators import CriticalThinkingEvaluator


async def main(path: str) -> int:
    inputs = json.load(open(path, encoding="utf-8"))
    inputs.pop("_note", None)
    evaluator = CriticalThinkingEvaluator(
        anthropic_api_key=os.environ["ANTHROPIC_API_KEY"], telemetry=False
    )

    started = time.monotonic()
    results = await asyncio.gather(
        *(evaluator.evaluate(**inputs) for _ in range(3)), return_exceptions=True
    )
    elapsed = time.monotonic() - started
    failures = 0
    for i, r in enumerate(results, start=1):
        if isinstance(r, Exception):
            failures += 1
            print(f"FAIL  call {i}: {type(r).__name__}: {r}")
        else:
            print(f"PASS  call {i}: {r.result.critical_thinking_score} ({r.metadata.processing_time_ms} ms)")
    print(f"      wall clock for all three: {elapsed:.1f}s (should be close to one call, not three)")

    try:
        evaluator.evaluate_sync(**inputs)
        failures += 1
        print("FAIL  evaluate_sync inside a running loop: it ran (expected a refusal)")
    except Exception as error:  # noqa: BLE001
        print(f"PASS  evaluate_sync inside a running loop refused: {type(error).__name__}: {error}")
    return 1 if failures else 0


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY in your shell or in a .env file (here or at the repo root) first.")
    sys.exit(asyncio.run(main(sys.argv[1])))
