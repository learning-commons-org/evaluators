"""Every contract in ``evals/`` has a registered Python class or an explicit allowlist entry.

Nearly every defect this suite exists to catch has the same shape: a registry fact was
copied into SDK code, the registry moved, and the copy silently kept working with the old
value. So each check reads the contract at test time and compares.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path

import pytest

import learning_commons_evaluators as sdk
from learning_commons_evaluators import read_outcome
from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.registry import EVALUATORS, index_by_id
from learning_commons_evaluators.evaluators.single_step import SingleStepEvaluator
from tests.unit.conftest import ProviderFactory

REPO_ROOT = Path(__file__).resolve().parents[5]
EVALS_ROOT = REPO_ROOT / "evals"

# Contracts with no Python implementation yet. Listing them here is what keeps them
# visible: the test below asserts that every contract on disk is either implemented or
# named here, so a new contract cannot sit unimplemented and unmentioned, and porting one
# without deleting its entry fails the build.
UNIMPLEMENTED: frozenset[str] = frozenset(
    {
        # Follow-on work in both SDKs (new family, claude-opus-5); on TS's allowlist too.
        "durable_skills.ela_writing.critical_thinking",
        # Phase 1a PR 4: multi-step.
        "student_facing_text.ela_reading.vocabulary_complexity",
        # Phase 2.
        "student_facing_text.ela_reading.meaning_directness",
        # Phase 3.
        "student_facing_text.ela_reading.background_knowledge_demands",
        "student_facing_text.ela_reading.organizational_structure",
        "student_facing_text.ela_reading.reference_knowledge_demands",
        "student_facing_text.ela_reading.sentence_structure",
        # Phase 4.
        "feedback.ela_writing.revision_accuracy",
        "feedback.ela_writing.revision_actionability",
        "feedback.ela_writing.revision_manageability",
        "feedback.ela_writing.strength_acknowledgment",
        "feedback.ela_writing.student_response_specificity",
        "feedback.ela_writing.withholding_answers",
        # Phase 5.
        "academic_standards_alignment.mathematics.math_standards_alignment",
    }
)

# Every evaluator the barrel exports, discovered rather than listed.
EXPORTED: list[type[BaseEvaluator]] = sorted(
    (
        value
        for value in vars(sdk).values()
        if isinstance(value, type)
        and issubclass(value, BaseEvaluator)
        and value not in (BaseEvaluator, SingleStepEvaluator)
        and hasattr(value, "metadata")
    ),
    key=lambda e: e.metadata.id,
)

CONTRACT_DIRS = sorted(p.parent for p in EVALS_ROOT.glob("*/*/*/config.json"))


def _contract_id(directory: Path) -> str:
    return json.loads((directory / "config.json").read_text(encoding="utf-8"))["evaluator"]["id"]


def test_discovery_finds_the_pilot() -> None:
    assert len(EXPORTED) == 3
    assert set(EXPORTED) == set(EVALUATORS)


class TestEveryContractIsImplementedOrListed:
    @pytest.mark.parametrize("directory", CONTRACT_DIRS, ids=lambda d: "/".join(d.parts[-3:]))
    def test_contract(self, directory: Path) -> None:
        evaluator_id = _contract_id(directory)
        implemented = {e.metadata.id for e in EXPORTED}
        if evaluator_id in implemented:
            assert evaluator_id not in UNIMPLEMENTED, (
                f'"{evaluator_id}" is implemented: drop it from UNIMPLEMENTED'
            )
        else:
            assert evaluator_id in UNIMPLEMENTED, (
                f'"{evaluator_id}" has a contract but no implementation and is not in UNIMPLEMENTED'
            )

    def test_the_allowlist_names_only_real_contracts(self) -> None:
        on_disk = {_contract_id(d) for d in CONTRACT_DIRS}
        assert on_disk >= UNIMPLEMENTED, UNIMPLEMENTED - on_disk


class TestNoIdCollisions:
    def test_current_and_historical_ids_name_one_evaluator_each(self) -> None:
        index = index_by_id(EVALUATORS)
        assert len(index) == sum(1 + len(e.metadata.id_history) for e in EVALUATORS)


@pytest.mark.parametrize("evaluator", EXPORTED, ids=lambda e: e.metadata.id)
class TestEachEvaluatorMatchesItsContract:
    def test_identity(self, evaluator: type[BaseEvaluator]) -> None:
        contract = load_contract(evaluator.metadata.id).evaluator
        assert evaluator.metadata.stable_id == contract.stable_id
        assert evaluator.metadata.id_history == tuple(contract.id_history)
        assert evaluator.metadata.name == contract.name
        assert evaluator.metadata.description == contract.description
        assert evaluator.metadata.supported_grades == tuple(contract.supported_grades)

    def test_modules_sit_at_the_path_derived_from_the_id(
        self, evaluator: type[BaseEvaluator]
    ) -> None:
        evaluator_id = evaluator.metadata.id
        assert evaluator.__module__ == f"learning_commons_evaluators.evaluators.{evaluator_id}"
        schema_module = importlib.import_module(
            f"learning_commons_evaluators.schemas.{evaluator_id}"
        )
        assert evaluator_id == schema_module.EVALUATOR_ID

    def test_input_and_output_models_are_the_generated_ones(
        self, evaluator: type[BaseEvaluator]
    ) -> None:
        assert issubclass(evaluator, SingleStepEvaluator)
        slug = evaluator.metadata.slug
        pascal = "".join(part.capitalize() for part in slug.split("_"))
        assert evaluator.input_model.__name__ == f"{pascal}Input"
        assert evaluator.output_model.__name__ == f"{pascal}Output"
        contract = load_contract(evaluator.metadata.id)
        assert list(evaluator.input_model.model_fields) == list(contract.input_schema["properties"])

    def test_default_providers_are_the_non_optional_steps(
        self, evaluator: type[BaseEvaluator]
    ) -> None:
        contract = load_contract(evaluator.metadata.id)
        assert list(evaluator.metadata.default_providers) == contract.providers

    def test_required_credentials_match(self, evaluator: type[BaseEvaluator]) -> None:
        contract = load_contract(evaluator.metadata.id)
        assert list(evaluator.metadata.required_credentials) == contract.required_credentials

    def test_outcome_names_fields_the_output_model_has(
        self, evaluator: type[BaseEvaluator]
    ) -> None:
        assert issubclass(evaluator, SingleStepEvaluator)
        outcome = evaluator.metadata.outcome
        assert outcome is not None, "every pilot evaluator produces a single judgement"
        assert outcome.score in evaluator.output_model.model_fields
        assert outcome.reasoning in evaluator.output_model.model_fields

    def test_grade_input_enum_agrees_with_supported_grades(
        self, evaluator: type[BaseEvaluator]
    ) -> None:
        contract = load_contract(evaluator.metadata.id)
        grade = contract.input_schema["properties"].get("grade_level")
        if grade is None:
            return
        assert tuple(grade["enum"]) == evaluator.metadata.supported_grades


@pytest.mark.parametrize("evaluator", EXPORTED, ids=lambda e: e.metadata.id)
class TestEachEvaluatorRunsItsContract:
    def _construct(self, evaluator: type[BaseEvaluator]) -> BaseEvaluator:
        keys = {f"{p.value}_api_key": "test-key" for p in evaluator.metadata.default_providers}
        return evaluator(**keys)

    async def test_the_temperature_sent_matches_the_contract(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator]
    ) -> None:
        contract = load_contract(evaluator.metadata.id)
        step = contract.step(f"evaluate_{evaluator.metadata.slug}")
        instance = self._construct(evaluator)
        await instance.evaluate(**_fixture_input(evaluator.metadata.id))
        assert providers.last.calls[0]["temperature"] == step.temperature

    async def test_every_declared_placeholder_reaches_the_prompt(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator]
    ) -> None:
        contract = load_contract(evaluator.metadata.id)
        step = contract.step(f"evaluate_{evaluator.metadata.slug}")
        assert step.prompt is not None
        await self._construct(evaluator).evaluate(**_fixture_input(evaluator.metadata.id))
        rendered = "\n".join(m["content"] for m in providers.last.calls[0]["messages"])
        for name in step.prompt.placeholders:
            assert f"{{{name}}}" not in rendered, f"{name} was not substituted"

    async def test_read_outcome_finds_a_verdict_in_the_returned_payload(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator]
    ) -> None:
        evaluation = await self._construct(evaluator).evaluate(
            **_fixture_input(evaluator.metadata.id)
        )
        assert read_outcome(evaluation, evaluator.metadata.outcome).score is not None

    async def test_a_declared_minimum_length_is_enforced(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator]
    ) -> None:
        contract = load_contract(evaluator.metadata.id)
        text_field, spec = next(
            (name, spec)
            for name, spec in contract.input_schema["properties"].items()
            if spec.get("type") == "string" and "enum" not in spec
        )
        minimum = spec.get("minLength", 1)
        inputs = {**_fixture_input(evaluator.metadata.id), text_field: "x" * (minimum - 1)}
        expected = "too short" if minimum > 1 else "cannot be empty"
        with pytest.raises(sdk.InputValidationError, match=expected):
            await self._construct(evaluator).evaluate(**inputs)


def _fixture_input(evaluator_id: str) -> dict[str, object]:
    """The first fixture case's inputs for an evaluator, as a caller would pass them."""
    contract = load_contract(evaluator_id)
    directory = next(d for d in CONTRACT_DIRS if _contract_id(d) == evaluator_id)
    case = json.loads(
        (
            directory
            / (
                contract.fixtures.path
                if contract.fixtures and contract.fixtures.path
                else "fixtures.json"
            )
        ).read_text()
    )[0]
    return dict(case["input"])
