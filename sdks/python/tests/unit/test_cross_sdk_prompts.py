"""Cross-SDK prompt check: Python renders the prompt the TypeScript SDK renders.

Both SDKs substitute a contract's declared placeholders into the verbatim prompt files with
plain text replacement. The TypeScript renderer (``createPromptRenderers``) is
``placeholderKeys.reduce((text, key) => text.replaceAll(`{${key}}`, inputs[key]), template)``;
that algorithm is re-stated here independently and run over every fixture so the two
renderings can be compared byte for byte. Placeholders bound to computed preprocessing
(``fk_score``) are masked, since ``textstat`` and ``text-readability`` disagree on syllable
counts, and their computed values are checked separately for shape.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from learning_commons_evaluators.contracts import Contract, load_contract
from learning_commons_evaluators.evaluators.inputs import validate_inputs
from learning_commons_evaluators.evaluators.registry import EVALUATORS
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator

REPO_ROOT = Path(__file__).resolve().parents[4]
EVALS_ROOT = REPO_ROOT / "evals"

COMPUTED = {"fk_score", "ground_truth_counts", "sentence_features"}
MASK = "<computed>"


def _fixtures(contract: Contract) -> list[dict]:
    directory = EVALS_ROOT.joinpath(
        *(s.replace("_", "-") for s in contract.evaluator.id.split("."))
    )
    path = (
        contract.fixtures.path if contract.fixtures and contract.fixtures.path else "fixtures.json"
    )
    return json.loads((directory / path).read_text(encoding="utf-8"))


CASES = [
    pytest.param(evaluator, case, id=f"{evaluator.metadata.slug}/{case['id']}")
    for evaluator in EVALUATORS
    for case in _fixtures(load_contract(evaluator.metadata.id))
]


def typescript_render(template: str, inputs: dict[str, str], keys: list[str]) -> str:
    text = template
    for key in keys:
        if key in inputs:
            text = text.replace("{" + key + "}", inputs[key])
    return text


@pytest.mark.parametrize(("evaluator", "case"), CASES)
def test_python_renders_what_typescript_renders(
    evaluator: type[SingleStepEvaluator], case: dict
) -> None:
    contract = evaluator.contract
    step = contract.step(f"evaluate_{contract.evaluator.slug}")
    assert step.prompt is not None
    keys = list(step.prompt.placeholders)

    keys_for_grades = {"grade_level": lambda v: str(v)}
    fields = {k: keys_for_grades.get(k, lambda v: v)(v) for k, v in case["input"].items()}
    values = validate_inputs(fields, contract.input_schema)

    # Python's rendering, with computed values masked.
    instance = evaluator.__new__(evaluator)
    python_inputs = evaluator._prompt_inputs(instance, values)
    computed = {k: v for k, v in python_inputs.items() if k in COMPUTED}
    masked_inputs = {k: (MASK if k in COMPUTED else v) for k, v in python_inputs.items()}
    python_messages = [
        typescript_render(contract.document(m.source_path), masked_inputs, keys)
        for m in step.prompt.messages
    ]
    # The SDK's own renderer must agree with the restated algorithm on the same inputs.
    from learning_commons_evaluators.prompts.render import render_prompt

    sdk_messages = [
        render_prompt(contract.document(m.source_path), masked_inputs, keys)
        for m in step.prompt.messages
    ]
    assert sdk_messages == python_messages

    # A TypeScript caller passes the same fixture with grade_level as the string token.
    typescript_inputs = {
        **{k: str(v) for k, v in case["input"].items()},
        **{k: MASK for k in computed},
    }
    typescript_messages = [
        typescript_render(contract.document(m.source_path), typescript_inputs, keys)
        for m in step.prompt.messages
    ]
    assert python_messages == typescript_messages

    for rendered in python_messages:
        for key in keys:
            assert "{" + key + "}" not in rendered, key

    # The masked values are numbers rounded to two places, as §10.4 requires of fk_score.
    for name, value in computed.items():
        assert re.fullmatch(r"-?\d+(\.\d{1,2})?", value), (name, value)


def test_the_check_covers_every_registered_evaluator() -> None:
    assert {p.values[0] for p in CASES} == set(EVALUATORS)
