"""Executable P1 review findings for the multi-step base — a temporary, self-deleting file.

Every test here asserts the behaviour the SDK spec calls for, and is marked
``xfail(strict=True)`` because the base does not do it yet. Two consequences:

* **Nothing here fails CI today.** A strict xfail that fails is reported as expected.
* **The moment a finding is fixed, its test fails loudly as XPASS.** That is the signal to
  delete the ``xfail`` marker, move the test into ``test_multi_step.py`` beside its
  siblings, and remove it from this file. When the file is empty, delete the file.

So this file is scaffolding, not a suite to maintain. If a test here is a duplicate of one
the fix already adds, or reads as low signal once the code is right, **delete it rather
than keeping it green** — each one exists to describe a defect, not to guard a behaviour
that better-placed tests already cover. Each finding's header says which case that applies
to, because the fixes overlap: P1-6 turns a runtime failure into a class-creation failure,
which makes one P1-1 case unreachable by construction.

P1-3 (a placeholder may read a later step) and P1-4 (a placeholder's target is never checked,
so an unbound optional one leaks a literal ``{name}`` into the prompt) were both confirmed but
dropped to P2 and removed from this file: ``scripts/checks/eval_config.py`` already enforces
step ordering and target existence in CI for every ``evals/`` config, and the SDK only ever
loads bundled generated contracts, so SDK-side checks there are defence-in-depth. Worth doing,
not worth blocking on.

Findings are P1-1, P1-5 and P1-6 from the review of #286. P1-2 (the ``running``
step-attribution in ``evaluate`` is dead code, because ``call_with_resampling`` has already
classified every provider failure by the time the except block sees it) has no observable
behaviour of its own to assert — it is resolved by deleting the attribution as part of the
P1-1 fix, and TestContractFaultsAreNotDependencyFailures is what proves it is gone.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest
from pydantic import BaseModel

from learning_commons_evaluators import ConfigurationError, DependencyError
from tests.unit.conftest import ProviderFactory
from tests.unit.evaluators import test_multi_step as demo
from tests.unit.evaluators.test_multi_step import INPUT, KEYS, ChainOutput, contract, define

#: The demo suite's recording-provider fixture, re-exported so pytest resolves it here too.
providers = demo.providers


class Notes(BaseModel):
    """A step output that is not the evaluator's result."""

    notes: str


def raw_contract() -> dict[str, Any]:
    """The shared two-step demo contract, as mutable JSON."""
    return copy.deepcopy(contract().model_dump(by_alias=True))


class TestContractFaultsAreNotDependencyFailures:
    """P1-1: a defect in ``config.json`` is reported as an LLM provider failure.

    ``evaluate`` raises bare ``ValueError`` for six contract faults inside its error
    boundary (multi_step.py:294, 362, 387, 418, 424, and the isinstance check at 228).
    Line 280 hands anything that is not already an ``EvaluatorError`` to
    ``wrap_provider_error``, which falls through to the ``DependencyError`` catch-all and
    stamps it with the ``dependency`` and ``model`` of whichever step line 278 picks. So a
    registry defect is reported as ``LLMProviderError(dependency="openai")``.

    Spec §6.1 classifies errors by fault domain — who must act — and §6.2 defines
    ``dependency`` as "the canonical ID of the failed **service**". Registry data is the
    caller/config domain, so ``ConfigurationError`` is the right class. Principle 4 rules
    out the current behaviour outright: "every error MUST be diagnosable from the error
    alone".

    The first case is the worst: no step runs at all, so line 278 falls back to
    ``self._steps[0]`` and names a vendor the evaluation never called.

    ``test_multi_step.py:521`` and ``:532`` currently assert ``LLMProviderError`` for two of
    these, so those two tests have to change with the fix.

    **The fix must cover ``single_step.py`` too.** The identical boundary is already merged
    there (``single_step.py:202-205`` over the bare ``ValueError`` at :230), so treating this
    as a multi-step defect leaves the two bases disagreeing about the same fault. The same
    applies to the P1-4 render leak, whose twin is ``single_step.py:236``.

    Scope note: the misclassification costs diagnosability, not retries — ``LLMProviderError``
    is non-retryable unless the status is 5xx, and these carry no status. And the worst
    sub-case below (no branch matches, so a vendor is named though nothing ran) is not
    reachable with today's bundled contracts, whose branches cover the whole input enum; it
    is a hazard for the next contract, not a live bug.

    **On fixing:** ``test_a_run_that_ends_on_a_non_output_step`` below becomes unreachable
    if P1-6 is fixed first (the contract is then rejected at class creation) — delete it
    rather than reworking it. The other two are genuinely runtime-only and should move into
    ``test_multi_step.py::TestFailures``.
    """

    @pytest.mark.xfail(strict=True, reason="P1-1: raised as LLMProviderError naming openai")
    async def test_no_branch_matching_the_inputs(self, providers: ProviderFactory) -> None:
        raw = raw_contract()
        for step in raw["steps"]:
            step["condition"] = {"input": "grade_level", "in": ["5"]}
        evaluator = define(steps=raw["steps"])(**KEYS)

        with pytest.raises(ConfigurationError) as failure:
            await evaluator.evaluate(**INPUT)

        # Nothing ran, so nothing can be attributed: naming a provider here is a factual
        # error about which service failed, not merely the wrong class.
        assert not isinstance(failure.value, DependencyError)
        assert providers.calls == []

    @pytest.mark.xfail(strict=True, reason="P1-1: raised as LLMProviderError naming google")
    async def test_two_entries_produce_one_output_for_the_same_inputs(
        self, providers: ProviderFactory
    ) -> None:
        raw = raw_contract()
        # rubric_low is grade 3 only; widen rubric_high to overlap it.
        raw["preprocessing"][2]["condition"] = {"input": "grade_level", "in": ["3", "4", "5"]}
        evaluator = define(preprocessing=raw["preprocessing"])(**KEYS)

        with pytest.raises(ConfigurationError):
            await evaluator.evaluate(**INPUT)

    @pytest.mark.xfail(strict=True, reason="P1-1: raised as LLMProviderError naming openai")
    async def test_a_required_placeholder_bound_to_an_optional_input(
        self, providers: ProviderFactory
    ) -> None:
        # The schema makes `note` optional; the placeholder makes it required. Only a run
        # that omits it can discover the disagreement, so this one cannot move to class
        # creation — it stays a runtime fault whatever else is fixed.
        raw = raw_contract()
        raw["input_schema"]["properties"]["note"] = {"type": "string"}
        raw["steps"][0]["prompt"]["placeholders"]["note"] = {
            "required": True,
            "source": "input.note",
        }
        raw["documents"]["notes-user.txt"] = "notes: {text} {note}"
        evaluator = define(
            steps=raw["steps"], documents=raw["documents"], input_schema=raw["input_schema"]
        )(**KEYS)

        with pytest.raises(ConfigurationError):
            await evaluator.evaluate(**INPUT)

    @pytest.mark.xfail(strict=True, reason="P1-1: raised as LLMProviderError naming google")
    async def test_a_run_that_ends_on_a_non_output_step(self, providers: ProviderFactory) -> None:
        # Delete this case if P1-6 lands first: the contract is then refused at class
        # creation and this run never starts.
        raw = raw_contract()
        raw["steps"][1]["condition"] = {"input": "grade_level", "in": ["5"]}
        evaluator = define(steps=raw["steps"])(**KEYS)

        with pytest.raises(ConfigurationError):
            await evaluator.evaluate(**INPUT)


class TestStepModelsAgreesWithTheContractsParser:
    """P1-5: ``step_models`` silently overrides the contract's ``parser``.

    Every step in ``evals/`` declares ``parser: {"kind": "structured_output"}``. The base
    never reads ``step.parser`` — ``_run_step`` (multi_step.py:305-324) branches on
    ``step_models[step.id] is None`` alone — so declaring a step as prose in Python calls it
    as free text against a contract that says otherwise, and nothing objects.

    That puts the decision about how a step is called in a Python dict rather than in the
    contract, which is what the module's docstring says it exists to prevent, and it lets
    Python and TypeScript call the same step two different ways with no check to catch it.

    The safe, minimal fix is one-directional: have ``_check_steps`` reject a ``None``
    ``step_models`` entry for a step whose ``parser.kind`` is ``structured_output``. That
    needs no new contract semantics and is enough to stop the drift.

    Going further — treating a *missing* ``parser`` as declaring a prose step — is an
    inference, not established: ``sdks/SPEC.md`` never mentions ``parser`` at all (§10.1
    lists model, prompt, temperature, ``optional`` and ``required_credentials``), and
    ``config.schema.json`` permits only ``structured_output``. So how a prose step is
    declared is a registry and spec decision before it is an SDK one.

    Note the demo contract in ``test_multi_step.py`` is itself inconsistent here: it declares
    ``parser: structured_output`` on the ``notes`` step that ``define()`` runs as prose, which
    is why nothing caught this.

    **On fixing:** keep the first test. The second encodes the inferred "missing parser means
    prose" semantics — delete it unless that decision is actually taken.
    """

    @pytest.mark.xfail(strict=True, reason="P1-5: step.parser is never read")
    def test_refuses_a_prose_step_the_contract_declares_as_structured(self) -> None:
        # The demo contract declares `parser: structured_output` on both steps, and the
        # shared `define()` helper calls `notes` as prose.
        with pytest.raises(ValueError, match="parser"):
            define()

    @pytest.mark.xfail(strict=True, reason="P1-5: step.parser is never read")
    def test_refuses_a_structured_step_the_contract_declares_as_prose(self) -> None:
        raw = raw_contract()
        del raw["steps"][0]["parser"]

        with pytest.raises(ValueError, match="parser"):
            define(steps=raw["steps"], step_models={"notes": Notes, "rate": ChainOutput})


class TestEveryStepThatCanEndARunProducesTheOutputModel:
    """P1-6: only the last declared step is checked, and a conditional last step breaks that.

    ``_check_steps:508-515`` validates ``contract.steps[-1]`` alone, on the stated grounds
    that "the contract's own last step is the one that always ends a run, whatever branch
    the inputs take". That holds only when the last step is unconditional, and
    ``evals/student-facing-text/ela-reading/vocabulary-complexity/config.json`` has a
    conditional one: its last step is gated on ``grade_level in ["5".."12"]``, so a grade-3
    run ends on ``vocab_complexity_grades_3_4``, a step nothing validates.

    A branch whose terminal step returns the wrong model therefore imports cleanly and fails
    at evaluation, mislabelled per P1-1.

    The fix needs care, and the obvious rule is wrong. "Every step from the last
    unconditional one onward" rejects vocabulary-complexity itself: its last unconditional
    step is ``background_knowledge``, whose output feeds the next prompt and is not the
    evaluator's result. The rule that accepts that contract is **every step *after* the last
    unconditional one**, plus the last unconditional step only when nothing follows it.

    That still leaves a hole: when a trailing group of conditional steps is not exhaustive
    over the input schema's enum, the run ends on the last unconditional step and fails at
    evaluation anyway. Closing it properly means either checking the conditions for
    exhaustiveness, or requiring the contract's last step to be unconditional. Which of the
    three to adopt is a maintainer decision, not something this test settles — it asserts
    only that the grade-3 branch terminal must be rejected, which all three rules agree on.

    Either way, rewrite the comment at :508-509, which states an invariant the contracts do
    not satisfy.

    **On fixing:** keep this test, and delete
    ``TestContractFaultsAreNotDependencyFailures::test_a_run_that_ends_on_a_non_output_step``
    above, which this makes unreachable.
    """

    @pytest.mark.xfail(strict=True, reason="P1-6: only contract.steps[-1] is checked")
    def test_refuses_a_conditional_branch_ending_on_a_non_output_step(self) -> None:
        raw = raw_contract()
        # Shaped like vocabulary-complexity: an unconditional first step, then one
        # conditional step per grade band. The grade-3 branch ends on `notes_grade_3`,
        # which produces Notes rather than the evaluator's output model.
        raw["steps"] = [
            raw["steps"][0],
            {
                **copy.deepcopy(raw["steps"][0]),
                "id": "notes_grade_3",
                "condition": {"input": "grade_level", "in": ["3"]},
            },
            {**raw["steps"][1], "condition": {"input": "grade_level", "in": ["4", "5"]}},
        ]

        with pytest.raises(ValueError, match="notes_grade_3"):
            define(
                steps=raw["steps"],
                step_models={"notes": None, "notes_grade_3": Notes, "rate": ChainOutput},
            )
