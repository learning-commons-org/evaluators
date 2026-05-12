"""Unit tests for :class:`~learning_commons_evaluators.evaluators.base.BaseEvaluator`.

Covers ``evaluate`` wiring: :class:`~learning_commons_evaluators.schemas.metadata.EvaluationMetadata`
always receives ``input.input_metadata()`` (PII-safe field summaries), regardless of
``send_full_input_with_telemetry`` on config. Also covers ``execute_step`` and
``evaluate`` error propagation via a minimal concrete evaluator.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from learning_commons_evaluators import (
    BaseEvaluator,
    EvaluationExplanation,
    TextComplexityEvaluationInput,
    create_config,
)
from learning_commons_evaluators.schemas.common_inputs import GradeInputField, TextInputField
from learning_commons_evaluators.schemas.config import EvaluationSettings
from learning_commons_evaluators.schemas.errors import ValidationError
from learning_commons_evaluators.schemas.input_specs import GradeInputSpec, TextInputSpec
from learning_commons_evaluators.schemas.metadata import (
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
)
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityAnswer,
    TextComplexityResult,
)


class _StubSettings(EvaluationSettings):
    """Minimal settings model for stub evaluator."""


def _stub_input() -> TextComplexityEvaluationInput:
    return TextComplexityEvaluationInput(
        text=TextInputField(spec=TextInputSpec(name="text"), value="hello world"),
        grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=3),
    )


class _StubEvaluator(
    BaseEvaluator[TextComplexityEvaluationInput, TextComplexityResult, _StubSettings]
):
    metadata = EvaluatorMetadata(
        id="stub-evaluator",
        version="0",
        name="Stub",
        description="Unit test stub.",
        maturity=EvaluatorMaturity.beta,
    )
    default_evaluation_settings = _StubSettings()

    def evaluate_impl(
        self,
        input: TextComplexityEvaluationInput,
        evaluation_settings: _StubSettings,
        evaluation_metadata,
    ) -> TextComplexityResult:
        return TextComplexityResult(
            answer=TextComplexityAnswer.SLIGHTLY_COMPLEX,
            explanation=EvaluationExplanation(summary="stub", details={}),
            metadata=evaluation_metadata,
        )


@pytest.fixture
def stub_evaluator(config):
    return _StubEvaluator(config)


class TestEvaluateInputMetadata:
    def test_evaluate_sets_metadata_from_input_metadata(self, stub_evaluator):
        inp = _stub_input()
        result = stub_evaluator.evaluate(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": "11"}
        assert result.metadata.input_metadata["grade_level"] == {"grade": 3}

    def test_full_telemetry_config_still_uses_input_metadata_not_raw_values(self, stub_evaluator):
        """``send_full_input_with_telemetry`` does not replace ``input_metadata`` with raw values."""
        # Re-bind evaluator with telemetry + full-input flag (same class, new config).
        cfg = create_config(telemetry_id="test", send_full_input_with_telemetry=True)
        ev = _StubEvaluator(cfg)
        inp = _stub_input()
        result = ev.evaluate(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": "11"}
        assert result.metadata.input_metadata["grade_level"] == {"grade": 3}


class TestEvaluateErrorHandling:
    def test_raises_validation_error_for_invalid_input(self, stub_evaluator):
        inp = TextComplexityEvaluationInput(
            text=TextInputField(
                spec=TextInputSpec(name="text", min_text_length=100),
                value="short",
            ),
            grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=3),
        )
        with pytest.raises(ValidationError):
            stub_evaluator.evaluate(inp)

    def test_propagates_evaluate_impl_exception(self, stub_evaluator):
        with (
            patch.object(stub_evaluator, "evaluate_impl", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            stub_evaluator.evaluate(_stub_input())


class TestExecuteStep:
    def test_returns_implementation_result(self, stub_evaluator, evaluation_metadata):
        assert stub_evaluator.execute_step("s", evaluation_metadata, lambda: "ok") == "ok"

    def test_records_failed_status_on_exception(self, stub_evaluator, evaluation_metadata):
        failing = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            stub_evaluator.execute_step("s", evaluation_metadata, failing)
        assert evaluation_metadata.step_details["s"].status == Status.failed
        assert "boom" in evaluation_metadata.step_details["s"].error_details
