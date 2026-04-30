"""Contract test harness: LLM mocking and prompt-request assertions.

Usage
-----
::

    case = load_conventionality_turnip_case()
    config = create_config_no_telemetry()
    evaluator = ConventionalityEvaluator(config)

    inp = ConventionalityEvaluationInput(
        text=case.input["text"],
        grade=case.input["grade"],
    )

    with ContractTestHarness(case) as harness:
        result = evaluator.evaluate(inp)

    harness.assert_prompt_step("main")

For evaluators with multiple LLM steps the harness automatically queues
responses in ``prompt_steps`` order and captures each call's request, so the
assertions still use the step name::

    harness.assert_prompt_step("step_1")
    harness.assert_prompt_step("step_2")

The captured data is accessible after the context exits.

Prompt strings (system and user) are compared after normalizing line endings
(``\\r\\n`` → ``\\n``) and stripping leading/trailing whitespace, so minor TOML
multiline formatting differences do not fail tests.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

from .loader import ContractCase, PromptStepContract

# The module-level name that ``base.py`` imports ``create_provider`` under.
_CREATE_PROVIDER_TARGET = "learning_commons_evaluators.evaluators.base.create_provider"


class ContractTestHarness:
    """Sets up a mocked LLM for a contract test and captures what was sent to it.

    The harness patches ``create_provider`` so that no real API calls are made.
    Each call to ``create_provider`` pops the next response from the case's
    ``prompt_steps`` (in order) and returns a lightweight callable that:

    - Records the formatted messages it receives.
    - Returns an ``AIMessage`` with the stored ``llm_response`` content.

    After the ``with`` block, use :meth:`assert_prompt_step` to verify each
    captured request matches the stored contract.
    """

    def __init__(self, case: ContractCase) -> None:
        self.case = case
        # Populated during the evaluation run; indexed by call order.
        self._captured: list[_CapturedCall] = []
        self._patch: Any = None

    def __enter__(self) -> ContractTestHarness:
        # Build a FIFO list of (step_name, response) pairs in definition order.
        self._response_queue: list[tuple[str, str]] = [
            (name, step.llm_response) for name, step in self.case.prompt_steps.items()
        ]
        self._captured = []

        self._patch = patch(_CREATE_PROVIDER_TARGET, side_effect=self._make_fake_provider)
        self._patch.start()
        return self

    def __exit__(self, *args: Any) -> None:
        if self._patch is not None:
            self._patch.stop()

    # ------------------------------------------------------------------
    # Assertions
    # ------------------------------------------------------------------

    def assert_prompt_step(self, step_name: str) -> None:
        """Assert that the request captured for *step_name* matches the contract.

        Raises:
            AssertionError: If the captured messages, model, or temperature
                differ from the stored contract.
            IndexError: If no call was captured for the given step.
        """
        step_names = list(self.case.prompt_steps.keys())
        if step_name not in step_names:
            raise ValueError(f"Step '{step_name}' not in contract. Available steps: {step_names}")
        step_index = step_names.index(step_name)

        if step_index >= len(self._captured):
            raise AssertionError(
                f"No LLM call captured for step '{step_name}' "
                f"(only {len(self._captured)} call(s) were made)."
            )

        captured = self._captured[step_index]
        contract = self.case.prompt_steps[step_name]
        _assert_prompt_matches(captured, contract, step_name)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _make_fake_provider(self, prompt_settings: Any, evaluator_config: Any) -> Any:
        """Return a callable that records input messages and returns the next mock response."""
        from langchain_core.messages import AIMessage

        if not self._response_queue:
            raise RuntimeError(
                "ContractTestHarness: more LLM calls were made than there are "
                "prompt steps in the contract case."
            )
        _step_name, response_content = self._response_queue.pop(0)
        captured_list = self._captured

        def _fake_llm(prompt_value: Any) -> AIMessage:
            # ``prompt_value`` is a ChatPromptValue produced by the template.
            messages = (
                prompt_value.to_messages()
                if hasattr(prompt_value, "to_messages")
                else list(prompt_value)
            )
            system_content = _message_content(messages, "system")
            human_content = _message_content(messages, "human")
            captured_list.append(
                _CapturedCall(
                    system_prompt=system_content,
                    user_prompt=human_content,
                    model=prompt_settings.model,
                    temperature=prompt_settings.temperature,
                )
            )
            return AIMessage(content=response_content)

        return _fake_llm


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


class _CapturedCall:
    """One captured LLM invocation."""

    def __init__(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float,
    ) -> None:
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.model = model
        self.temperature = temperature


def _message_content(messages: list[Any], message_type: str) -> str:
    """Extract content from the first message of the given type."""
    for msg in messages:
        if getattr(msg, "type", None) == message_type:
            return str(msg.content)
    return ""


def _normalize_prompt_snapshot(s: str) -> str:
    """Normalize prompt text for contract comparison.

    Hand-edited or pasted TOML multiline strings may differ from runtime only by
    CRLF vs LF line endings, or a spurious leading newline after an opening
    ``'''`` delimiter (TOML trims only the first newline). Normalizing avoids
    those false failures while preserving internal content.
    """
    return s.replace("\r\n", "\n").strip()


def _assert_prompt_matches(
    captured: _CapturedCall,
    contract: PromptStepContract,
    step_name: str,
) -> None:
    assert captured.model == contract.model, (
        f"Step '{step_name}': model mismatch.\n"
        f"  SDK sent:  {captured.model!r}\n"
        f"  Contract:  {contract.model!r}"
    )
    assert captured.temperature == contract.temperature, (
        f"Step '{step_name}': temperature mismatch.\n"
        f"  SDK sent:  {captured.temperature}\n"
        f"  Contract:  {contract.temperature}"
    )
    sys_sdk = _normalize_prompt_snapshot(captured.system_prompt)
    sys_contract = _normalize_prompt_snapshot(contract.system_prompt)
    assert sys_sdk == sys_contract, (
        f"Step '{step_name}': system_prompt mismatch.\n"
        f"  First diff at char {_first_diff_index(sys_sdk, sys_contract)}.\n"
        f"  SDK sent (first 200):  {sys_sdk[:200]!r}\n"
        f"  Contract (first 200):  {sys_contract[:200]!r}"
    )
    user_sdk = _normalize_prompt_snapshot(captured.user_prompt)
    user_contract = _normalize_prompt_snapshot(contract.user_prompt)
    assert user_sdk == user_contract, (
        f"Step '{step_name}': user_prompt mismatch.\n"
        f"  SDK sent:  {user_sdk!r}\n"
        f"  Contract:  {user_contract!r}"
    )


def _first_diff_index(a: str, b: str) -> int:
    for i, (ca, cb) in enumerate(zip(a, b, strict=False)):
        if ca != cb:
            return i
    return min(len(a), len(b))
