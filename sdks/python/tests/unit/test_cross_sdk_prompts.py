"""Cross-SDK prompt check: Python renders the prompt the TypeScript SDK renders.

Both SDKs substitute a contract's declared placeholders into the verbatim prompt files with
plain text replacement. The TypeScript renderer (``createPromptRenderers``) is
``placeholderKeys.reduce((text, key) => text.replaceAll(`{${key}}`, inputs[key]), template)``;
that algorithm is re-stated here independently, and so is the choice of value for every
placeholder, then both are run over every fixture of every registered evaluator so the two
renderings can be compared byte for byte.

Two kinds of value are masked rather than compared. Computed preprocessing (``fk_score``,
``ground_truth_counts``, ``sentence_features``) is masked because the contracts name a
different library per language — ``textstat`` here, ``text-readability`` and
``compromise``/``syllable`` there — and those disagree on syllable counts by design; their
shape is checked separately below and their arithmetic in the feature tests. A step's output
is masked because reaching it means calling a model. Everything else, including a rubric
loaded from a contract document, is compared as rendered.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from learning_commons_evaluators.contracts import Contract, load_contract
from learning_commons_evaluators.contracts.loader import Preprocessing, Step
from learning_commons_evaluators.dependencies.knowledge_graph import LearningComponent
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    MathStandardsAlignmentEvaluator,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.inputs import validate_inputs
from learning_commons_evaluators.evaluators.multi_step import MultiStepEvaluator
from learning_commons_evaluators.evaluators.registry import EVALUATORS
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator, step_for
from learning_commons_evaluators.features.preprocessing import format_number, run_preprocessing_step
from learning_commons_evaluators.prompts.render import render_prompt

REPO_ROOT = Path(__file__).resolve().parents[4]
EVALS_ROOT = REPO_ROOT / "evals"

#: Preprocessing outputs each SDK computes with its own language's library.
COMPUTED = {"fk_score", "ground_truth_counts", "sentence_features"}
MASK = "<computed>"


def _fixtures(contract: Contract) -> list[dict[str, Any]]:
    directory = EVALS_ROOT.joinpath(
        *(s.replace("_", "-") for s in contract.evaluator.id.split("."))
    )
    path = (
        contract.fixtures.path if contract.fixtures and contract.fixtures.path else "fixtures.json"
    )
    return json.loads((directory / path).read_text(encoding="utf-8"))


#: Every registered evaluator paired with each of its contract's fixture cases.
PAIRS: list[tuple[type[BaseEvaluator], dict[str, Any]]] = [
    (evaluator, case)
    for evaluator in EVALUATORS
    for case in _fixtures(load_contract(evaluator.metadata.id))
]

CASES = [
    pytest.param(evaluator, case, id=f"{evaluator.metadata.slug}/{case['id']}")
    for evaluator, case in PAIRS
]


def typescript_render(template: str, inputs: Mapping[str, str], keys: list[str]) -> str:
    """``createPromptRenderers``, restated."""
    text = template
    for key in keys:
        if key in inputs:
            text = text.replace("{" + key + "}", inputs[key])
    return text


def plan_for(evaluator: type[BaseEvaluator], values: Mapping[str, str]) -> list[Step]:
    """The steps these inputs run, in declared order, read off the contract."""
    contract = evaluator.contract
    if not issubclass(evaluator, MultiStepEvaluator):
        return [step_for(contract)]
    return [
        step for step in contract.steps if step.condition is None or step.condition.holds(values)
    ]


def entry_producing(contract: Contract, output: str, values: Mapping[str, str]) -> Preprocessing:
    """The one preprocessing entry that produces ``output`` for these inputs."""
    applicable = [
        entry
        for entry in contract.preprocessing
        if entry.output == output and (entry.condition is None or entry.condition.holds(values))
    ]
    assert len(applicable) == 1, (output, [e.id for e in applicable])
    return applicable[0]


def typescript_inputs(
    evaluator: type[BaseEvaluator], step: Step, values: Mapping[str, str]
) -> dict[str, str]:
    """What a TypeScript caller's renderer receives for one step, from the contract alone.

    A caller passes ``grade_level`` as the string token there, which is what ``values``
    already holds after validation: Python's ``int`` convenience (§2.3) is normalised before
    anything renders, so both SDKs bind the same characters.
    """
    contract = evaluator.contract
    assert step.prompt is not None
    resolved: dict[str, str] = {}
    for name, placeholder in step.prompt.placeholders.items():
        source = placeholder.source
        if source == "input":
            resolved[name] = values[name]
        elif source.startswith("input."):
            resolved[name] = values[source.removeprefix("input.")]
        elif source.startswith("steps."):
            resolved[name] = MASK
        else:
            output = source.removeprefix("preprocessing.")
            entry = entry_producing(contract, output, values)
            if entry.type == "api":
                # Fetched at run time from the Knowledge Graph, so there is no value to
                # compare offline; the format both SDKs build it in is checked below.
                resolved[name] = MASK
            else:
                resolved[name] = (
                    MASK if output in COMPUTED else contract.document(entry.source_path or "")
                )
    return resolved


def python_inputs(
    evaluator: type[BaseEvaluator], step: Step, values: Mapping[str, str]
) -> dict[str, str]:
    """The SDK's own placeholder values for one step, with the masked sources pre-seeded.

    Seeding rather than computing-then-replacing is what keeps this a rendering test: a
    computation whose value would be masked never runs, so neither does the step it reads.
    """
    instance = evaluator.__new__(evaluator)
    if isinstance(instance, MultiStepEvaluator):
        outputs = {declared.id: MASK for declared in evaluator.contract.steps}
        return instance._prompt_inputs(step, values, outputs, {output: MASK for output in COMPUTED})
    if not isinstance(instance, SingleStepEvaluator):
        # An evaluator that renders its own prompts rather than being built by a factory.
        # It binds the caller's inputs by name; a placeholder it fills from a live fetch
        # has no offline value, so it is masked on both sides here.
        assert step.prompt is not None
        return {
            name: values[name] if placeholder.source == "input" else MASK
            for name, placeholder in step.prompt.placeholders.items()
        }
    computed = instance._prompt_inputs(values)
    return {k: (MASK if k in COMPUTED else v) for k, v in computed.items()}


@pytest.mark.parametrize(("evaluator", "case"), CASES)
def test_python_renders_what_typescript_renders(
    evaluator: type[BaseEvaluator], case: dict[str, Any]
) -> None:
    contract = evaluator.contract
    values = validate_inputs(case["input"], contract.input_schema)
    plan = plan_for(evaluator, values)
    assert plan, "every fixture runs at least one step"

    for step in plan:
        assert step.prompt is not None
        keys = list(step.prompt.placeholders)
        ours = python_inputs(evaluator, step, values)
        theirs = typescript_inputs(evaluator, step, values)

        for message in step.prompt.messages:
            template = contract.document(message.source_path)
            # The SDK's renderer must agree with the restated algorithm on the same inputs,
            # and the two SDKs' inputs must agree, so the renderings agree byte for byte.
            rendered = render_prompt(template, ours, keys)
            assert rendered == typescript_render(template, ours, keys)
            assert rendered == typescript_render(template, theirs, keys), (step.id, message.role)
            for key in keys:
                assert "{" + key + "}" not in rendered, (step.id, key)


def test_the_learning_component_list_is_formatted_as_typescript_formats_it() -> None:
    """The one placeholder no contract describes: a list the SDK builds in code.

    Masked in the rendering check above because it is fetched at run time, so it is
    compared here instead. TypeScript builds it as ``components.map((lc, i) =>
    `${i + 1}. [${lc.identifier}] ${lc.description}`).join('\n')``; that is restated here
    the way this module restates the renderer, so both SDKs send the model the same
    characters for the same components. The numbering is one-based and the identifier is
    bracketed in both, which is what lets each SDK check that every component it sent was
    judged.
    """
    components = [
        LearningComponent(identifier="lc-1", description="Add within 20"),
        LearningComponent(identifier="lc-2", description="Subtract within 20"),
    ]
    typescript = "\n".join(
        f"{index + 1}. [{lc.identifier}] {lc.description}" for index, lc in enumerate(components)
    )

    instance = MathStandardsAlignmentEvaluator.__new__(MathStandardsAlignmentEvaluator)
    rendered = "\n".join(
        message["content"] for message in instance._render_messages("What is 2 + 2?", components)
    )

    assert typescript in rendered
    assert "{learning_components}" not in rendered


#: Kinds a contract supplies in code rather than by a library call over the input text.
IN_CODE_KINDS = ("custom", "load_rubric_text")


def test_library_computations_bind_a_number_rounded_as_declared() -> None:
    """Every entry a contract computes by library call binds a number, rounded as declared.

    Masked in the rendering check above, so checked here: §10.4 pins ``fk_score`` to two
    places, and this is what holds the Python value to the shape the TypeScript value has.
    The entries a contract names as ``custom`` are blocks and JSON rather than numbers, and
    their arithmetic is covered by the feature tests.
    """
    checked = 0
    for evaluator, case in PAIRS:
        contract = evaluator.contract
        values = validate_inputs(case["input"], contract.input_schema)
        for entry in contract.preprocessing:
            if entry.kind in IN_CODE_KINDS or entry.python is None:
                continue
            if entry.condition is not None and not entry.condition.holds(values):
                continue
            transform = entry.python.post_transform
            places = (transform.precision or 0) if transform else 0
            rendered = format_number(
                run_preprocessing_step(values[entry.input or ""], entry.python)
            )
            assert re.fullmatch(rf"-?\d+(\.\d{{1,{places}}})?", rendered), (entry.id, rendered)
            checked += 1
    # The masks above hide these values, so a check that silently covered none of them
    # would leave the whole §10.4 guarantee untested.
    assert checked, "no fixture exercised a library computation"


def test_the_check_covers_every_registered_evaluator() -> None:
    assert {evaluator for evaluator, _ in PAIRS} == set(EVALUATORS)
