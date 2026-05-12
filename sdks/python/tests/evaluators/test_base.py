"""Tests for :class:`~learning_commons_evaluators.evaluators.base.BaseEvaluator`.

Covers: ``__init__``, ``evaluate`` (metadata, settings override, success/failure),
``update_total_token_usage``, ``execute_step``, ``execute_prompt_chain_step``.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError

from learning_commons_evaluators import (
    BaseEvaluator,
    EvaluationExplanation,
    TextComplexityEvaluationInput,
    create_config,
    create_config_no_telemetry,
)
from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.schemas.common_inputs import GradeInputField, TextInputField
from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    LlmProvider,
    PromptSettings,
)
from learning_commons_evaluators.schemas.errors import APIError, EvaluatorError, ValidationError
from learning_commons_evaluators.schemas.input_specs import GradeInputSpec, TextInputSpec
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
    TokenUsage,
)
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityAnswer,
    TextComplexityResult,
)

_CHAIN_PATCH = "learning_commons_evaluators.evaluators.base.create_provider"


class _ChainOutput(BaseModel):
    """Minimal LLM JSON payload model (stand-in for conventionality output models)."""

    label: str = Field(description="short label")
    score: int = Field(description="numeric score")


_CHAIN_JSON = '{"label": "ok", "score": 7}'


class _StubSettings(EvaluationSettings):
    """Minimal settings; ``marker`` supports tests that pass explicit ``evaluation_settings``."""

    marker: int = 0


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
            explanation=EvaluationExplanation(
                summary="stub",
                details={"marker": evaluation_settings.marker},
            ),
            metadata=evaluation_metadata,
        )


@pytest.fixture
def stub_evaluator(config):
    return _StubEvaluator(config)


# ---------------------------------------------------------------------------
# BaseEvaluator.__init__
# ---------------------------------------------------------------------------


class TestBaseEvaluatorInit:
    def test_config_is_stored(self, config):
        assert _StubEvaluator(config).config is config


# ---------------------------------------------------------------------------
# evaluate()
# ---------------------------------------------------------------------------


class TestEvaluateSuccess:
    def test_sets_status_succeeded_and_processing_time(self, stub_evaluator):
        result = stub_evaluator.evaluate(_stub_input())
        assert result.metadata.status == Status.succeeded
        assert result.metadata.processing_time_ms >= 0.0

    def test_passes_explicit_evaluation_settings(self, stub_evaluator):
        custom = _StubSettings(marker=42)
        result = stub_evaluator.evaluate(_stub_input(), evaluation_settings=custom)
        assert result.metadata.evaluation_settings.marker == 42
        assert result.explanation.details.get("marker") == 42


class TestEvaluateInputMetadata:
    """``input_metadata`` on :class:`EvaluationMetadata` always comes from ``input.input_metadata()``."""

    def test_evaluate_sets_metadata_from_input_metadata(self, stub_evaluator):
        inp = _stub_input()
        result = stub_evaluator.evaluate(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": 11}
        assert result.metadata.input_metadata["grade_level"] == {"grade": 3}

    def test_full_telemetry_config_still_uses_input_metadata_not_raw_values(self, stub_evaluator):
        cfg = create_config(telemetry_partner_id="test", send_full_input_with_telemetry=True)
        ev = _StubEvaluator(cfg)
        inp = _stub_input()
        result = ev.evaluate(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": 11}
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

    def test_validation_failure_emits_end_log_with_failed_status(self, stub_evaluator):
        captured: list = []

        class _Capture(logging.Handler):
            def emit(self, record: logging.LogRecord) -> None:
                meta = getattr(record, "evaluation_metadata", None)
                if meta is not None and record.getMessage() == "evaluation end":
                    captured.append(meta)

        h = _Capture()
        stub_evaluator.config.logger.addHandler(h)
        stub_evaluator.config.logger.setLevel(logging.INFO)
        try:
            inp = TextComplexityEvaluationInput(
                text=TextInputField(
                    spec=TextInputSpec(name="text", min_text_length=100),
                    value="short",
                ),
                grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=3),
            )
            with pytest.raises(ValidationError):
                stub_evaluator.evaluate(inp)
        finally:
            stub_evaluator.config.logger.removeHandler(h)

        assert captured
        assert captured[-1].status == Status.failed
        assert captured[-1].error_details


# ---------------------------------------------------------------------------
# update_total_token_usage
# ---------------------------------------------------------------------------


class TestUpdateTotalTokenUsage:
    def test_inserts_usage_for_new_provider(self, stub_evaluator, evaluation_metadata):
        usage = TokenUsage(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        stub_evaluator.update_total_token_usage(usage, evaluation_metadata)
        stored = evaluation_metadata.total_token_usage[LlmProvider.GOOGLE]
        assert stored.input_tokens == 10
        assert stored.output_tokens == 5

    def test_accumulates_usage_for_existing_provider(self, stub_evaluator, evaluation_metadata):
        evaluation_metadata.total_token_usage[LlmProvider.GOOGLE] = TokenUsage(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        stub_evaluator.update_total_token_usage(
            TokenUsage(
                provider_type=LlmProvider.GOOGLE,
                model="gemini-2.0-flash",
                input_tokens=20,
                output_tokens=15,
            ),
            evaluation_metadata,
        )
        stored = evaluation_metadata.total_token_usage[LlmProvider.GOOGLE]
        assert stored.input_tokens == 30
        assert stored.output_tokens == 20


# ---------------------------------------------------------------------------
# execute_step
# ---------------------------------------------------------------------------


class TestExecuteStep:
    def test_returns_implementation_result(self, stub_evaluator, evaluation_metadata):
        assert (
            stub_evaluator.execute_step("s", evaluation_metadata, lambda: "the-result")
            == "the-result"
        )

    def test_records_succeeded_status_on_success(self, stub_evaluator, evaluation_metadata):
        stub_evaluator.execute_step("s", evaluation_metadata, lambda: None)
        assert evaluation_metadata.step_details["s"].status == Status.succeeded

    def test_records_failed_status_and_error_on_exception(
        self, stub_evaluator, evaluation_metadata
    ):
        failing = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            stub_evaluator.execute_step("s", evaluation_metadata, failing)
        step = evaluation_metadata.step_details["s"]
        assert step.status == Status.failed
        assert "boom" in step.error_details

    def test_re_raises_exception(self, stub_evaluator, evaluation_metadata):
        failing = MagicMock(side_effect=RuntimeError("inner"))
        with pytest.raises(RuntimeError, match="inner"):
            stub_evaluator.execute_step("s", evaluation_metadata, failing)

    def test_extras_appear_in_step_metadata(self, stub_evaluator, evaluation_metadata):
        stub_evaluator.execute_step("s", evaluation_metadata, lambda: None, extras={"k": "v"})
        assert evaluation_metadata.step_details["s"].extras["k"] == "v"


# ---------------------------------------------------------------------------
# execute_prompt_chain_step
# ---------------------------------------------------------------------------


class TestExecutePromptChainStep:
    """Mock ``create_provider`` so ``template | provider`` runs in-process (matches sdk_python tests)."""

    def test_returns_raw_string_when_parser_output_type_is_none(self, evaluation_metadata):
        def _fake_llm(_pv):
            return AIMessage(content="plain prose")

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        ev = _StubEvaluator(create_config_no_telemetry())
        with patch(_CHAIN_PATCH, return_value=_fake_llm):
            out = ev.execute_prompt_chain_step(
                step_name="raw",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=None,
            )
        assert out == "plain prose"

    def test_returns_parsed_pydantic_output(self, stub_evaluator, evaluation_metadata):
        def _fake_llm(_pv):
            return AIMessage(content=_CHAIN_JSON)

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with patch(_CHAIN_PATCH, return_value=_fake_llm):
            result = stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=_ChainOutput,
            )
        assert isinstance(result, _ChainOutput)
        assert result.label == "ok"
        assert result.score == 7

    def test_parser_returning_model_instance_short_circuits_model_validate(
        self, stub_evaluator, evaluation_metadata
    ):
        """When ``JsonOutputParser.invoke`` returns a model, ``isinstance`` path skips ``model_validate``."""
        prebuilt = _ChainOutput(label="direct", score=99)

        def _fake_llm(_pv):
            return AIMessage(content="unused")

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_llm),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.return_value = prebuilt
            mock_parser_cls.return_value = mock_parser
            result = stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=_ChainOutput,
            )
        assert result is prebuilt

    def test_keyboard_interrupt_from_parser_propagates(self, stub_evaluator, evaluation_metadata):
        def _fake_llm(_pv):
            return AIMessage(content=_CHAIN_JSON)

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_llm),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.side_effect = KeyboardInterrupt
            mock_parser_cls.return_value = mock_parser
            with pytest.raises(KeyboardInterrupt):
                stub_evaluator.execute_prompt_chain_step(
                    step_name="main",
                    prompt_settings=PromptSettings(
                        provider_type=LlmProvider.GOOGLE,
                        model="gemini-2.0-flash",
                        temperature=0.0,
                    ),
                    evaluation_metadata=evaluation_metadata,
                    template=template,
                    chain_inputs={"input": "Hello"},
                    parser_output_type=_ChainOutput,
                )

    def test_system_exit_from_parser_propagates(self, stub_evaluator, evaluation_metadata):
        def _fake_llm(_pv):
            return AIMessage(content=_CHAIN_JSON)

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_llm),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.side_effect = SystemExit(3)
            mock_parser_cls.return_value = mock_parser
            with pytest.raises(SystemExit) as exc_info:
                stub_evaluator.execute_prompt_chain_step(
                    step_name="main",
                    prompt_settings=PromptSettings(
                        provider_type=LlmProvider.GOOGLE,
                        model="gemini-2.0-flash",
                        temperature=0.0,
                    ),
                    evaluation_metadata=evaluation_metadata,
                    template=template,
                    chain_inputs={"input": "Hello"},
                    parser_output_type=_ChainOutput,
                )
            assert exc_info.value.code == 3

    def test_prompt_settings_recorded_in_step_extras(self, stub_evaluator, evaluation_metadata):
        settings = PromptSettings(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            temperature=0.0,
        )
        template = ChatPromptTemplate.from_messages([("human", "{input}")])

        with patch(_CHAIN_PATCH, return_value=lambda _pv: AIMessage(content=_CHAIN_JSON)):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=settings,
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

        step = evaluation_metadata.step_details["main"]
        assert step.extras[PROMPT_STEP_EXTRA_PROMPT_SETTINGS]["model"] == "gemini-2.0-flash"
        assert PROMPT_STEP_EXTRA_TOKEN_USAGE in step.extras

    def test_token_usage_recorded_when_llm_reports_usage(self, stub_evaluator, evaluation_metadata):
        def _llm_with_usage(_pv):
            return AIMessage(
                content=_CHAIN_JSON,
                usage_metadata={
                    "input_tokens": 42,
                    "output_tokens": 17,
                    "total_tokens": 59,
                },
            )

        settings = PromptSettings(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            temperature=0.0,
        )
        template = ChatPromptTemplate.from_messages([("human", "{input}")])

        with patch(_CHAIN_PATCH, return_value=_llm_with_usage):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=settings,
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

        step = evaluation_metadata.step_details["main"]
        assert step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE]["input_tokens"] == 42
        assert step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE]["output_tokens"] == 17
        assert evaluation_metadata.total_token_usage[LlmProvider.GOOGLE].input_tokens == 42

    def test_propagates_configuration_error_from_create_provider(
        self, stub_evaluator, evaluation_metadata
    ):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(
                _CHAIN_PATCH,
                side_effect=ConfigurationError("Google provider config is not set"),
            ),
            pytest.raises(ConfigurationError, match="Google provider config is not set"),
        ):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    def test_propagates_evaluator_error_without_wrapping(self, stub_evaluator, evaluation_metadata):
        """``EvaluatorError`` subclasses raised inside the chain are re-raised unchanged."""
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, side_effect=EvaluatorError("bare evaluator error")),
            pytest.raises(EvaluatorError, match="bare evaluator error"),
        ):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    def test_wraps_unexpected_chain_failure_as_api_error(self, stub_evaluator, evaluation_metadata):
        def _boom(_pv):
            raise ValueError("simulated provider failure")

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_boom),
            pytest.raises(APIError, match="simulated provider failure"),
        ):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    def test_malformed_llm_json_raises_api_error(self, stub_evaluator, evaluation_metadata):
        """Invalid JSON from the LLM becomes :class:`APIError` via ``wrap_provider_error``."""

        def _bad(_pv):
            return AIMessage(content="not-json")

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_bad),
            pytest.raises(APIError, match="Invalid json output"),
        ):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    def test_schema_mismatch_raises_pydantic_validation_error(
        self, stub_evaluator, evaluation_metadata
    ):
        """Valid JSON that does not satisfy the output model raises Pydantic ``ValidationError``."""

        def _partial(_pv):
            return AIMessage(content='{"label": "only"}')

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_partial),
            pytest.raises(PydanticValidationError),
        ):
            stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )
