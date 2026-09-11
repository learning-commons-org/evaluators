"""Parser unit tests: hand-written payloads per ``output_schema.json`` against the generated models.

These take over the parsing coverage the 0.2.0 recorded-response contract tests provided.
Every bundled contract gets a schema-driven round trip; the four pilot evaluators also get
hand-written payloads and the rejections a strict parser must make.
"""

from __future__ import annotations

import importlib
from typing import Any

import pytest
from pydantic import BaseModel, ValidationError

from learning_commons_evaluators.contracts import list_contract_ids, load_contract
from learning_commons_evaluators.schemas.feedback.ela_writing.tone_appropriateness import (
    ToneAppropriatenessInput,
    ToneAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.feedback.ela_writing.withholding_answers import (
    WithholdingAnswersOutput,
)
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.grade_level_appropriateness import (
    GradeBand,
    GradeLevelAppropriatenessInput,
    GradeLevelAppropriatenessOutput,
)
from learning_commons_evaluators.schemas.student_facing_text.ela_reading.vocabulary_complexity import (
    GRADE_LEVEL_VALUES,
    VocabularyComplexityInput,
    VocabularyComplexityOutput,
)


def _pascal(slug: str) -> str:
    return "".join(part.capitalize() for part in slug.split("_"))


def output_model(evaluator_id: str) -> type[BaseModel]:
    module = importlib.import_module(f"learning_commons_evaluators.schemas.{evaluator_id}")
    model = getattr(module, f"{_pascal(evaluator_id.rsplit('.', 1)[-1])}Output")
    assert issubclass(model, BaseModel)
    return model


def input_model(evaluator_id: str) -> type[BaseModel]:
    module = importlib.import_module(f"learning_commons_evaluators.schemas.{evaluator_id}")
    model = getattr(module, f"{_pascal(evaluator_id.rsplit('.', 1)[-1])}Input")
    assert issubclass(model, BaseModel)
    return model


def sample(node: dict[str, Any], defs: dict[str, Any]) -> Any:
    """A minimal instance of a JSON Schema node, for the schema-driven round trip."""
    if "$ref" in node:
        target = defs[node["$ref"].removeprefix("#/$defs/")]
        return sample({**target, **{k: v for k, v in node.items() if k != "$ref"}}, defs)
    if "enum" in node:
        return node["enum"][0]
    declared = node.get("type")
    if isinstance(declared, list):
        declared = next(t for t in declared if t != "null")
    if declared == "string":
        return "x" * max(1, int(node.get("minLength", 1)))
    if declared == "integer":
        return int(node.get("minimum", 0))
    if declared == "number":
        return float(node.get("minimum", 0))
    if declared == "boolean":
        return True
    if declared == "array":
        return [sample(node["items"], defs)]
    if declared == "object":
        return {
            name: sample(spec, defs)
            for name, spec in node.get("properties", {}).items()
            if name in node.get("required", [])
        }
    raise AssertionError(f"unsupported node {node!r}")


@pytest.mark.parametrize("evaluator_id", list_contract_ids())
class TestEveryContract:
    def test_output_model_accepts_a_schema_conforming_payload(self, evaluator_id: str) -> None:
        schema = load_contract(evaluator_id).output_schema
        payload = sample(schema, schema.get("$defs", {}))
        parsed = output_model(evaluator_id).model_validate(payload)
        assert parsed.model_dump(exclude_none=True) == payload

    def test_output_model_mirrors_the_schema_properties_and_required(
        self, evaluator_id: str
    ) -> None:
        schema = load_contract(evaluator_id).output_schema
        emitted = output_model(evaluator_id).model_json_schema()
        assert list(emitted["properties"]) == list(schema["properties"])
        assert sorted(emitted.get("required", [])) == sorted(schema.get("required", []))
        assert emitted.get("additionalProperties") is False

    def test_output_model_rejects_an_extra_property(self, evaluator_id: str) -> None:
        schema = load_contract(evaluator_id).output_schema
        payload = {**sample(schema, schema.get("$defs", {})), "unexpected": 1}
        with pytest.raises(ValidationError):
            output_model(evaluator_id).model_validate(payload)

    def test_input_model_takes_the_placeholder_names(self, evaluator_id: str) -> None:
        schema = load_contract(evaluator_id).input_schema
        assert list(input_model(evaluator_id).model_fields) == list(schema["properties"])

    def test_outcome_fields_exist_on_the_model(self, evaluator_id: str) -> None:
        contract = load_contract(evaluator_id)
        if contract.outcome is not None:
            fields = output_model(evaluator_id).model_fields
            assert contract.outcome.score in fields
            assert contract.outcome.reasoning in fields


class TestGradeLevelAppropriateness:
    PAYLOAD = {
        "reasoning": "1. Quantitative ... 2. Qualitative ... 3. Background ... 4. Synthesis ...",
        "grade_band": "4-5",
        "alternative_grade_band": "2-3",
        "scaffolding_needed": "Pre-teach the vocabulary; read aloud.",
    }

    def test_parses_a_grade_band_verdict(self) -> None:
        parsed = GradeLevelAppropriatenessOutput.model_validate(self.PAYLOAD)
        assert parsed.grade_band == "4-5"
        assert parsed.alternative_grade_band == "2-3"

    def test_rejects_a_single_grade_where_a_band_is_required(self) -> None:
        with pytest.raises(ValidationError):
            GradeLevelAppropriatenessOutput.model_validate({**self.PAYLOAD, "grade_band": "4"})

    def test_rejects_a_missing_field(self) -> None:
        payload = {k: v for k, v in self.PAYLOAD.items() if k != "scaffolding_needed"}
        with pytest.raises(ValidationError):
            GradeLevelAppropriatenessOutput.model_validate(payload)

    def test_grade_band_alias_lists_the_six_bands(self) -> None:
        assert GradeBand.__args__ == ("K-1", "2-3", "4-5", "6-8", "9-10", "11-12")  # type: ignore[attr-defined]

    def test_input_is_text_only(self) -> None:
        assert list(GradeLevelAppropriatenessInput.model_fields) == ["text"]
        with pytest.raises(ValidationError):
            GradeLevelAppropriatenessInput(text="t", grade_level=5)  # type: ignore[call-arg]


class TestVocabularyComplexity:
    PAYLOAD = {
        "tier_2_words": "devastating, ancient",
        "tier_3_words": "mitochondria",
        "archaic_words": "",
        "other_complex_words": "powerhouse (idiom)",
        "complexity_score": "moderately_complex",
        "reasoning": "Some domain terms with contextual support.",
    }

    def test_parses_a_complexity_verdict(self) -> None:
        parsed = VocabularyComplexityOutput.model_validate(self.PAYLOAD)
        assert parsed.complexity_score == "moderately_complex"

    def test_rejects_a_label_outside_the_scale(self) -> None:
        with pytest.raises(ValidationError):
            VocabularyComplexityOutput.model_validate(
                {**self.PAYLOAD, "complexity_score": "complex"}
            )

    def test_rejects_a_numeric_score(self) -> None:
        # The other-grades prompt asks for a bare integer; the contract requires the label.
        with pytest.raises(ValidationError):
            VocabularyComplexityOutput.model_validate({**self.PAYLOAD, "complexity_score": 2})

    def test_input_takes_an_int_grade_and_exposes_the_accepted_tokens(self) -> None:
        assert VocabularyComplexityInput(text="t", grade_level=7).grade_level == 7
        assert GRADE_LEVEL_VALUES == ("3", "4", "5", "6", "7", "8", "9", "10", "11", "12")


class TestFeedbackFamily:
    def _key_feature(self, met: int = 1) -> dict[str, Any]:
        return {"met": met, "justification": "Because."}

    def test_tone_appropriateness_parses_a_binary_verdict(self) -> None:
        payload = {
            "reasoning": "The feedback is neutral and about the work.",
            "key_features": {
                "neutral_professional_language": self._key_feature(),
                "targets_work_not_student": self._key_feature(),
                "praise_proportionate_to_work": self._key_feature(0),
            },
            "proposed_adjustment": "Already meets the criterion.",
            "quality_score": 1,
        }
        parsed = ToneAppropriatenessOutput.model_validate(payload)
        assert parsed.quality_score == 1
        assert parsed.key_features.praise_proportionate_to_work.met == 0

    def test_quality_score_is_binary(self) -> None:
        payload = {
            "reasoning": "r",
            "key_features": {
                "points_toward_evidence_without_supplying": self._key_feature(),
                "prompts_revision_without_rewriting": self._key_feature(),
                "leaves_core_thinking_to_student": self._key_feature(),
            },
            "proposed_adjustment": "p",
            "quality_score": 1,
        }
        assert WithholdingAnswersOutput.model_validate(payload).quality_score == 1
        with pytest.raises(ValidationError):
            WithholdingAnswersOutput.model_validate({**payload, "quality_score": 0.5})
        with pytest.raises(ValidationError):
            WithholdingAnswersOutput.model_validate({**payload, "quality_score": 2})

    def test_key_features_are_evaluator_specific(self) -> None:
        # Tone's features on Withholding Answers is a schema mismatch, not a near miss.
        payload = {
            "reasoning": "r",
            "key_features": {
                "neutral_professional_language": self._key_feature(),
                "targets_work_not_student": self._key_feature(),
                "praise_proportionate_to_work": self._key_feature(),
            },
            "proposed_adjustment": "p",
            "quality_score": 0,
        }
        with pytest.raises(ValidationError):
            WithholdingAnswersOutput.model_validate(payload)

    def test_two_text_input(self) -> None:
        inp = ToneAppropriatenessInput(student_text="s", feedback_text="f")
        assert (inp.student_text, inp.feedback_text) == ("s", "f")
