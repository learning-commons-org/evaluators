"""The bundled contracts read back as the registry declared them."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

from learning_commons_evaluators.contracts import (
    Condition,
    Contract,
    contract_path,
    list_contract_ids,
    load_contract,
)
from learning_commons_evaluators.providers import Provider

REPO_ROOT = Path(__file__).resolve().parents[5]
EVALS_ROOT = REPO_ROOT / "evals"

# The four forms a placeholder source may take, from config.schema.json.
SOURCE = re.compile(
    r"^(input|input\.[A-Za-z_][A-Za-z0-9_]*|preprocessing\.[A-Za-z_][A-Za-z0-9_]*"
    r"|steps\.[A-Za-z_][A-Za-z0-9_]*\.output)$"
)

GLA = "student_facing_text.ela_reading.grade_level_appropriateness"
VOCAB = "student_facing_text.ela_reading.vocabulary_complexity"
TONE = "feedback.ela_writing.tone_appropriateness"
MATH = "academic_standards_alignment.mathematics.math_standards_alignment"
CRITICAL_THINKING = "durable_skills.ela_writing.critical_thinking"


def registry_ids() -> list[str]:
    return sorted(
        json.loads(path.read_text(encoding="utf-8"))["evaluator"]["id"]
        for path in EVALS_ROOT.glob("*/*/*/config.json")
    )


@pytest.fixture(params=registry_ids())
def contract(request: pytest.FixtureRequest) -> Contract:
    return load_contract(request.param)


class TestBundleMatchesTheRegistry:
    def test_every_registry_contract_is_bundled(self) -> None:
        assert list_contract_ids() == registry_ids()
        assert len(list_contract_ids()) >= 17

    def test_config_is_bundled_verbatim(self, contract: Contract) -> None:
        segments = contract.evaluator.id.split(".")
        source = next(
            p
            for p in EVALS_ROOT.glob("*/*/*/config.json")
            if json.loads(p.read_text())["evaluator"]["id"] == contract.evaluator.id
        )
        bundled = contract_path(contract.evaluator.id) / "config.json"
        assert bundled.read_bytes() == source.read_bytes()
        assert [s.replace("_", "-") for s in segments] == list(
            source.parent.relative_to(EVALS_ROOT).parts
        )

    def test_every_named_document_is_present_and_matches_its_declared_sha256(
        self, contract: Contract
    ) -> None:
        declared: dict[str, str | None] = {}
        for step in contract.steps:
            for message in step.prompt.messages if step.prompt else []:
                declared[message.source_path] = message.sha256
        for entry in contract.preprocessing:
            if entry.source_path:
                declared[entry.source_path] = entry.sha256
        assert set(contract.documents) == set(declared)
        for source_path, sha in declared.items():
            if sha is not None:
                actual = hashlib.sha256(contract.documents[source_path].encode("utf-8")).hexdigest()
                assert actual == sha, source_path

    def test_documents_are_verbatim_bytes(self, contract: Contract) -> None:
        for source_path, text in contract.documents.items():
            assert (contract_path(contract.evaluator.id) / source_path).read_bytes() == text.encode(
                "utf-8"
            )


class TestContractShape:
    def test_identity_fields(self, contract: Contract) -> None:
        assert contract.evaluator.id.count(".") == 2
        assert re.fullmatch(r"[0-9a-fA-F-]{36}", contract.evaluator.stable_id)
        assert contract.evaluator.name.endswith("Evaluator")
        assert contract.evaluator.supported_grades
        assert contract.evaluator.slug == contract.evaluator.id.rsplit(".", 1)[-1]

    def test_schemas_are_resolved_inline(self, contract: Contract) -> None:
        assert contract.input_schema["type"] == "object"
        assert "properties" in contract.input_schema
        assert contract.output_schema["type"] == "object"
        assert "properties" in contract.output_schema

    def test_every_llm_step_declares_prompt_model_and_generation(self, contract: Contract) -> None:
        for step in contract.steps:
            if step.type == "llm":
                assert step.prompt is not None and step.prompt.messages
                assert step.model is not None and step.model.name
                assert isinstance(step.model.provider, Provider)
                assert step.generation is not None

    def test_placeholder_sources_take_one_of_the_four_forms_and_resolve(
        self, contract: Contract
    ) -> None:
        inputs = set(contract.input_schema["properties"])
        outputs = {e.output for e in contract.preprocessing if e.output}
        seen_steps: set[str] = set()
        for step in contract.steps:
            for name, placeholder in (step.prompt.placeholders if step.prompt else {}).items():
                assert SOURCE.match(placeholder.source), (step.id, name, placeholder.source)
                kind, _, rest = placeholder.source.partition(".")
                if placeholder.source == "input":
                    assert name in inputs, (step.id, name)
                elif kind == "input":
                    assert rest in inputs, (step.id, name)
                elif kind == "preprocessing":
                    assert rest in outputs, (step.id, name)
                else:
                    assert rest.removesuffix(".output") in seen_steps, (step.id, name)
            seen_steps.add(step.id)

    def test_outcome_names_output_properties(self, contract: Contract) -> None:
        if contract.outcome is not None:
            assert contract.outcome.score in contract.output_schema["properties"]
            assert contract.outcome.reasoning in contract.output_schema["properties"]

    def test_every_prompt_placeholder_is_declared(self, contract: Contract) -> None:
        # A ``{token}`` in a template that no placeholder declares would be sent verbatim.
        for step in contract.steps:
            if step.prompt is None:
                continue
            declared = set(step.prompt.placeholders)
            for message in step.prompt.messages:
                for token in re.findall(
                    r"(?<!\{)\{([a-z_][a-z0-9_]*)\}(?!\})", contract.document(message.source_path)
                ):
                    assert token in declared, (contract.evaluator.id, step.id, token)


class TestLookups:
    def test_step_by_id(self) -> None:
        step = load_contract(VOCAB).step("vocab_complexity_grades_3_4")
        assert step.model is not None
        assert step.model.provider is Provider.GOOGLE
        assert step.condition is not None
        assert step.condition.values == ["3", "4"]
        assert step.temperature == 0

    def test_unknown_step_names_the_contract(self) -> None:
        with pytest.raises(
            LookupError, match='Step "nope" not found in Vocabulary Complexity Evaluator'
        ):
            load_contract(VOCAB).step("nope")

    def test_preprocessing_entry_and_python_binding(self) -> None:
        entry = load_contract(VOCAB).preprocessing_entry("fk_score")
        assert entry.python is not None
        assert (entry.python.library, entry.python.function) == ("textstat", "flesch_kincaid_grade")
        assert entry.python.post_transform is not None
        assert entry.python.post_transform.precision == 2
        assert entry.condition is not None and entry.condition.holds({"grade_level": "3"})
        assert not entry.condition.holds({"grade_level": "7"})

    def test_unknown_preprocessing_and_document(self) -> None:
        with pytest.raises(LookupError, match='Preprocessing "nope"'):
            load_contract(GLA).preprocessing_entry("nope")
        with pytest.raises(LookupError, match='names "nope.txt"'):
            load_contract(GLA).document("nope.txt")

    def test_temperature_null_is_none(self) -> None:
        step = load_contract(CRITICAL_THINKING).step("evaluate_critical_thinking")
        assert step.temperature is None

    def test_required_credentials_skip_optional_steps(self) -> None:
        math = load_contract(MATH)
        assert math.required_credentials == ["learning_commons_api_key"]
        assert load_contract(TONE).required_credentials == []

    def test_providers_in_declared_order_excluding_optional_steps(self) -> None:
        assert load_contract(VOCAB).providers == [Provider.OPENAI, Provider.GOOGLE]
        assert load_contract(MATH).providers == [Provider.ANTHROPIC]
        assert load_contract(GLA).providers == [Provider.GOOGLE]

    def test_condition_values_are_strings_even_when_declared_as_numbers(self) -> None:
        condition = Condition.model_validate({"input": "grade_level", "in": [3, "4"]})
        assert condition.values == ["3", "4"]
        assert condition.holds({"grade_level": "3"})

    def test_unknown_contract(self) -> None:
        with pytest.raises(FileNotFoundError, match="No bundled contract for 'nope.nope.nope'"):
            load_contract("nope.nope.nope")

    def test_loading_is_cached(self) -> None:
        assert load_contract(GLA) is load_contract(GLA)

    def test_contracts_are_immutable(self) -> None:
        with pytest.raises(Exception, match="frozen"):
            load_contract(GLA).evaluator.id = "x"  # type: ignore[misc]
