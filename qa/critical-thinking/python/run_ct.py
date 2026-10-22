"""Run the Critical Thinking evaluator on one input file and print the result.

Usage (from qa/critical-thinking):
    export ANTHROPIC_API_KEY=...   # or put it in .env
    ./run.sh py inputs/A-three-passages-mixed.json
    ./run.sh py inputs/B-one-passage.json --spy-telemetry
    ./run.sh py inputs/B-one-passage.json --no-telemetry

The SDK never reads keys from the environment; this script does, and passes the key in.
Each run is one paid model call (roughly $0.03-$0.19 depending on input size).
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from learning_commons_evaluators import CriticalThinkingEvaluator

LEVELS = ["not_evident", "exploring", "analyzing", "integrating", "extending"]


def median_rating(ratings: list[str]) -> str:
    """Median of the ratings on LEVELS order, rounding up on an even count (prompt rule 6)."""
    ordered = sorted(LEVELS.index(r) for r in ratings)
    return LEVELS[ordered[len(ordered) // 2]]


def spy_on_telemetry() -> None:
    """Print every telemetry event body to stderr before it is sent."""
    import learning_commons_evaluators.telemetry.client as client

    original = client._post

    def spy(http, delivery):  # noqa: ANN001
        print(f"[telemetry] {delivery.body}", file=sys.stderr)
        original(http, delivery)

    client._post = spy


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_file")
    parser.add_argument("--spy-telemetry", action="store_true", help="print telemetry events")
    parser.add_argument("--no-telemetry", action="store_true", help="run with telemetry=False")
    args = parser.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        print("Set ANTHROPIC_API_KEY in your shell or in a .env file (here or at the repo root) first.", file=sys.stderr)
        return 2

    if args.spy_telemetry:
        spy_on_telemetry()

    with open(args.input_file, encoding="utf-8") as f:
        inputs = json.load(f)
    inputs.pop("_note", None)

    evaluator = CriticalThinkingEvaluator(
        anthropic_api_key=key, telemetry=not args.no_telemetry
    )
    try:
        evaluation = evaluator.evaluate_sync(**inputs)
    except Exception as error:  # noqa: BLE001 - report whatever the SDK raised
        print(f"{type(error).__name__}: {error}")
        return 1

    envelope_json = evaluation.model_dump_json(indent=2)
    print(envelope_json)

    # Read the serialized envelope, as an integrator storing JSON would. Scenario D3 checks
    # that an unrated synthesizing_sources is absent here, not present as null.
    envelope = json.loads(envelope_json)
    indicators = envelope["result"]["indicators"]
    ratings = [v["rating"] for v in indicators.values() if v]
    score = envelope["result"]["critical_thinking_score"]
    print("\n--- summary ---")
    print(f"passages:               {len(inputs.get('source_passages', []))}")
    print(f"indicators rated:       {', '.join(indicators)}")
    synth = "absent"
    if "synthesizing_sources" in indicators:
        synth = "present" if indicators["synthesizing_sources"] else "present as null (bug?)"
    print(f"synthesizing_sources:   {synth}")
    print(f"score:                  {score}")
    print(f"score == median:        {score == median_rating(ratings)}")
    usage = evaluation.metadata.token_usage
    print(f"tokens in / out:        {usage.input_tokens} / {usage.output_tokens}")
    print(f"time:                   {evaluation.metadata.processing_time_ms} ms")
    return 0


if __name__ == "__main__":
    sys.exit(main())
