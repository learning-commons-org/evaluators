"""Validate each step's temperature against what its model actually accepts.

Newer reasoning models across all three providers we use have converged on
"don't send a temperature": Gemini 3 degrades (looping, worse reasoning) when
given one below 1.0, GPT-5 returns a 400 for anything but 1, and Claude's
Opus 5 / Opus 4.8 / 4.7 / Sonnet 5 / Fable 5 removed sampling parameters
outright. A config that sets `temperature: 0` against one of those is either
silently broken or silently worse -- neither surfaces as a test failure, which
is exactly why this check exists.

There is no API that reports a model's temperature policy, so the mapping is a
hand-maintained registry: evals/_schemas/model_constraints.json. Two design
choices make that list fail safely rather than rot:

  - It's data with provenance. Every family carries a `source` and a
    `verified` date, so the claim is re-checkable rather than folklore.
  - An UNLISTED model is an error, not a pass. Adopting a new model forces
    someone to look its policy up once and record it, instead of copy-pasting
    a temperature from a neighbouring config and finding out in production.

Rules, per llm step:
  default_only family + a number  -> error (must be null)
  tunable family      + null      -> error (a number is expected; null would
                                     silently hand control to the provider)
  model matches nothing           -> error (add a registry entry)
"""

from __future__ import annotations

import json
import os
import re

from .base import Check, Result, Violation, evaluator_configs, load_json, shared_schema_path

REGISTRY_PATH = shared_schema_path("model_constraints.json")


def _load_registry() -> list[dict]:
    return load_json(REGISTRY_PATH)["families"]


def _match(model_name: str, families: list[dict]) -> dict | None:
    for family in families:
        if re.search(family["pattern"], model_name):
            return family
    return None


class EvalModelConstraints(Check):
    name = "eval-model-constraints"
    description = "Check each step's temperature against its model's documented policy"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)

        if not os.path.exists(REGISTRY_PATH):
            result.violations.append(Violation(REGISTRY_PATH, "model constraints registry not found"))
            return result

        try:
            families = _load_registry()
        except (OSError, json.JSONDecodeError, KeyError) as e:
            result.violations.append(Violation(REGISTRY_PATH, f"unreadable registry: {e}"))
            return result

        for cfg_path in evaluator_configs():
            try:
                config = load_json(cfg_path)
            except (OSError, json.JSONDecodeError):
                continue  # eval-config reports unreadable configs

            for step in config.get("steps", []):
                if step.get("type") != "llm":
                    continue

                model_name = step.get("model", {}).get("name")
                if not model_name:
                    continue  # eval-config enforces model presence

                generation = step.get("generation", {})
                if "temperature" not in generation:
                    continue  # eval-config enforces the required key
                temperature = generation["temperature"]

                family = _match(model_name, families)
                where = f"steps[{step.get('id', '?')}]"

                if family is None:
                    result.violations.append(
                        Violation(
                            cfg_path,
                            f"{where}: model `{model_name}` matches no family in "
                            f"{REGISTRY_PATH}. Look up whether this model accepts a "
                            f"temperature and add an entry (with a source + verified "
                            f"date) rather than assuming it behaves like its predecessor",
                        )
                    )
                    continue

                constraint = family["constraint"]

                if constraint == "default_only" and temperature is not None:
                    result.violations.append(
                        Violation(
                            cfg_path,
                            f"{where}: `{model_name}` must not be sent a temperature "
                            f"(got {temperature!r}) -- set \"temperature\": null. "
                            f"{family['reason']} See {family['source']}",
                        )
                    )
                elif constraint == "tunable" and temperature is None:
                    result.violations.append(
                        Violation(
                            cfg_path,
                            f"{where}: `{model_name}` accepts a temperature, so null "
                            f"leaves the value to the provider's default implicitly. "
                            f"Set an explicit number, or move this model to a "
                            f"default_only family in {REGISTRY_PATH} if that's wrong",
                        )
                    )

        return result
