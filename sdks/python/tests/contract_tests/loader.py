"""Load contract test cases from evaluator settings folders.

Each evaluator's ``contracts.toml`` lives next to its ``settings.toml`` in
``sdks/settings/<evaluator>/`` (e.g.
``sdks/settings/conventionality/contracts.toml``).  This module provides the data
models and a loader that reads those files into structured objects usable from
tests.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from importlib.abc import Traversable
else:
    try:
        from importlib.resources.abc import Traversable
    except ImportError:
        from importlib.abc import Traversable

if sys.version_info >= (3, 11):
    import tomllib  # type: ignore[import-untyped]
else:
    try:
        import tomllib  # type: ignore[import-untyped, import-not-found]
    except ImportError:
        import tomli as tomllib  # type: ignore[import-not-found,no-redef]


# Sentinel used to detect placeholder values left by the TOML template.
_PLACEHOLDER_PREFIX = "PLACEHOLDER"


@dataclass
class PromptStepContract:
    """Contract for one LLM prompt step: the exact request sent and response received.

    ``system_prompt`` and ``user_prompt`` are the *fully formatted* messages —
    all template placeholders have been substituted (including library-computed
    values like ``{format_instructions}`` and ``{fk_score}``).

    ``llm_response`` is the raw string content returned by the LLM, as captured
    from the notebook run.  It is used to mock the LLM in the contract test.
    """

    system_prompt: str
    user_prompt: str
    model: str
    temperature: float
    llm_response: str

    def is_populated(self) -> bool:
        """Return False if any field still holds a placeholder value."""
        return not any(
            str(v).startswith(_PLACEHOLDER_PREFIX)
            for v in (self.system_prompt, self.user_prompt, self.llm_response)
        )


@dataclass
class ContractCase:
    """One test case for a contract test.

    Attributes:
        name:           Identifier matching the ``[cases.<name>]`` TOML key.
        description:    Human-readable label (optional).
        input:          Raw evaluator input values (e.g. ``{"text": ..., "grade": 4}``).
        prompt_steps:   Ordered mapping of step name → :class:`PromptStepContract`.
                        The order matches the order of LLM calls made during evaluation.
        expected_result: Parsed LLM output in notebook format (i.e. the dict produced by
                        ``JsonOutputParser``, before SDK result mapping).  Used to verify
                        the SDK produces the same structured result.
    """

    name: str
    description: str
    input: dict[str, Any]
    prompt_steps: dict[str, PromptStepContract]
    expected_result: dict[str, Any]

    def is_populated(self) -> bool:
        """Return False if any prompt step still holds a placeholder value."""
        return all(step.is_populated() for step in self.prompt_steps.values())

    def llm_responses_in_order(self) -> list[str]:
        """Return LLM responses for all steps, in call order."""
        return [step.llm_response for step in self.prompt_steps.values()]


def load_contract_case(evaluator_name: str, case_name: str) -> ContractCase:
    """Load a named test case from the evaluator's ``contracts.toml``.

    Resolved via :func:`~learning_commons_evaluators.settings.load_settings.shared_settings_root`
    (bundled ``settings/<evaluator_name>/contracts.toml`` in the package; kept in sync
    with the canonical ``sdks/settings/`` copy by ``make sync-settings``).

    Args:
        evaluator_name: Name of the evaluator (e.g. ``"conventionality"``).
        case_name:      Name of the case within the TOML (e.g. ``"turnip"``).

    Returns:
        A :class:`ContractCase` loaded from the TOML.

    Raises:
        FileNotFoundError: If ``contracts.toml`` does not exist.
        KeyError: If ``case_name`` is not found in the TOML.
    """
    toml_path = _settings_path(evaluator_name) / "contracts.toml"
    if not toml_path.is_file():
        raise FileNotFoundError(
            f"contracts.toml not found for evaluator '{evaluator_name}' (expected at {toml_path})"
        )

    if isinstance(toml_path, Path):
        with open(toml_path, "rb") as fh:
            data = tomllib.load(fh)
    else:
        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)

    cases = data.get("cases", {})
    if case_name not in cases:
        available = ", ".join(cases.keys()) or "(none)"
        raise KeyError(f"Case '{case_name}' not found in {toml_path}. Available cases: {available}")

    return _parse_case(case_name, cases[case_name])


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _settings_path(evaluator_name: str) -> Path | Traversable:
    """Resolve the settings directory for an evaluator from the shared settings root."""
    from learning_commons_evaluators.settings.load_settings import (
        shared_settings_root,  # noqa: PLC0415
    )

    return shared_settings_root() / evaluator_name


def _parse_case(name: str, raw: dict[str, Any]) -> ContractCase:
    prompt_steps_raw = raw.get("prompt_steps", {})
    prompt_steps: dict[str, PromptStepContract] = {
        step_name: _parse_prompt_step(step_data)
        for step_name, step_data in prompt_steps_raw.items()
    }
    return ContractCase(
        name=name,
        description=raw.get("description", ""),
        input=raw.get("input", {}),
        prompt_steps=prompt_steps,
        expected_result=raw.get("expected_result", {}),
    )


def _parse_prompt_step(raw: dict[str, Any]) -> PromptStepContract:
    return PromptStepContract(
        system_prompt=str(raw["system_prompt"]),
        user_prompt=str(raw["user_prompt"]),
        model=str(raw["model"]),
        temperature=float(raw["temperature"]),
        llm_response=str(raw["llm_response"]),
    )
