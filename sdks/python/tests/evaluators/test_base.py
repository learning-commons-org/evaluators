"""Tests for BaseEvaluator.

Covers: config wiring, evaluate() telemetry branching, error handling,
update_total_token_usage, execute_step, and execute_prompt_chain_step.
"""

from unittest.mock import MagicMock, patch

import pytest

from learning_commons_evaluators import (
    ConventionalityEvaluationInput,
    ConventionalityEvaluator,
    create_config,
    create_config_no_telemetry,
)
from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.schemas.config import LlmProvider, PromptSettings
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
    ConventionalityOutput,
)
from learning_commons_evaluators.schemas.errors import APIError, ValidationError
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    EvaluationMetadata,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
    TokenUsage,
)

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------


def _evaluator(*, send_full_input=False):
    """Return a ConventionalityEvaluator; use send_full_input=True to enable full-input telemetry."""
    if send_full_input:
        config = create_config(telemetry_id="test", send_full_input_with_telemetry=True)
    else:
        config = create_config_no_telemetry()
    return ConventionalityEvaluator(config)


def _meta():
    """Return a minimal EvaluationMetadata suitable for direct method tests."""
    return EvaluationMetadata(
        evaluator_metadata=EvaluatorMetadata(
            id="test",
            version="0.1",
            name="Test",
            description="Test",
            maturity=EvaluatorMaturity.beta,
        ),
        evaluation_settings=ConventionalityEvaluationSettings(),
        input_metadata={},
    )


# A realistic sample long enough to satisfy the min_text_length=100 constraint.
_SAMPLE_TEXT = (
    "Marco Polo was a Venetian merchant and explorer who traveled through Asia "
    "in the late 13th century. He spent nearly two decades at the court of "
    "Kublai Khan, the Mongol ruler of China, and described his experiences in "
    "a book that introduced Europeans to the Far East."
)


def _inp(text=_SAMPLE_TEXT, grade=5):
    return ConventionalityEvaluationInput(text=text, grade=grade)


# ConventionalityOutput used as a stand-in for the LLM-parsed output.
_MOCK_OUTPUT = ConventionalityOutput(
    complexity_score="moderately_complex",
    reasoning="Uses some conventional language.",
    conventionality_features=["idioms"],
    grade_context="Grade-appropriate.",
    instructional_insights="Consider scaffolding.",
)

# A minimal JSON body accepted by ConventionalityOutput's parser.
_CONV_JSON = (
    '{"complexity_score": "slightly_complex", "reasoning": "Clear.",'
    ' "conventionality_features": [], "grade_context": "Fine.", "instructional_insights": "None."}'
)

_CHAIN_PATCH = "learning_commons_evaluators.evaluators.base.create_provider"


# ---------------------------------------------------------------------------
# BaseEvaluator.__init__
# ---------------------------------------------------------------------------


class TestBaseEvaluatorInit:
    def test_config_is_stored(self):
        config = create_config_no_telemetry()
        assert ConventionalityEvaluator(config).config is config


# ---------------------------------------------------------------------------
# evaluate() — telemetry branching
# ---------------------------------------------------------------------------


class TestEvaluateTelemetryBranching:
    def test_uses_input_metadata_by_default(self):
        """When send_full_input_with_telemetry=False, input.input_metadata() is used."""
        evaluator = _evaluator()
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_MOCK_OUTPUT):
            result = evaluator.evaluate(_inp())
        # input_metadata() returns shape metadata, not the raw text value.
        assert result.metadata.input_metadata["text"] == {"textLength": str(len(_SAMPLE_TEXT))}

    def test_uses_input_values_when_full_telemetry_enabled(self):
        """When send_full_input_with_telemetry=True, input.input_values() is used."""
        evaluator = _evaluator(send_full_input=True)
        with patch.object(evaluator, "execute_prompt_chain_step", return_value=_MOCK_OUTPUT):
            result = evaluator.evaluate(_inp())
        # input_values() returns the raw text string, not {"textLength": ...}.
        assert result.metadata.input_metadata["text"] == _SAMPLE_TEXT
        assert result.metadata.input_metadata["grade"] == 5


# ---------------------------------------------------------------------------
# evaluate() — error handling
# ---------------------------------------------------------------------------


class TestEvaluateErrorHandling:
    def test_raises_validation_error_for_invalid_input(self):
        # "x" is below the 100-char minimum defined in the TOML settings.
        evaluator = _evaluator()
        invalid = ConventionalityEvaluationInput(text="x", grade=5)
        with pytest.raises(ValidationError):
            evaluator.evaluate(invalid)

    def test_propagates_evaluate_impl_exception(self):
        evaluator = _evaluator()
        with (
            patch.object(evaluator, "evaluate_impl", side_effect=RuntimeError("boom")),
            pytest.raises(RuntimeError, match="boom"),
        ):
            evaluator.evaluate(_inp())


# ---------------------------------------------------------------------------
# update_total_token_usage
# ---------------------------------------------------------------------------


class TestUpdateTotalTokenUsage:
    def test_inserts_usage_for_new_provider(self, evaluation_metadata):
        evaluator = _evaluator()
        usage = TokenUsage(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        evaluator.update_total_token_usage(usage, evaluation_metadata)
        stored = evaluation_metadata.total_token_usage[LlmProvider.GOOGLE]
        assert stored.input_tokens == 10
        assert stored.output_tokens == 5

    def test_accumulates_usage_for_existing_provider(self, evaluation_metadata):
        evaluator = _evaluator()
        evaluation_metadata.total_token_usage[LlmProvider.GOOGLE] = TokenUsage(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        evaluator.update_total_token_usage(
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
    def test_returns_implementation_result(self, evaluation_metadata):
        result = _evaluator().execute_step("s", evaluation_metadata, lambda: "the-result")
        assert result == "the-result"

    def test_records_succeeded_status_on_success(self, evaluation_metadata):
        _evaluator().execute_step("s", evaluation_metadata, lambda: None)
        assert evaluation_metadata.step_details["s"].status == Status.succeeded

    def test_records_failed_status_and_error_on_exception(self, evaluation_metadata):
        failing = MagicMock(side_effect=ValueError("boom"))
        with pytest.raises(ValueError, match="boom"):
            _evaluator().execute_step("s", evaluation_metadata, failing)
        step = evaluation_metadata.step_details["s"]
        assert step.status == Status.failed
        assert "boom" in step.error_details

    def test_re_raises_exception(self, evaluation_metadata):
        failing = MagicMock(side_effect=RuntimeError("inner"))
        with pytest.raises(RuntimeError, match="inner"):
            _evaluator().execute_step("s", evaluation_metadata, failing)

    def test_extras_appear_in_step_metadata(self, evaluation_metadata):
        _evaluator().execute_step("s", evaluation_metadata, lambda: None, extras={"k": "v"})
        assert evaluation_metadata.step_details["s"].extras["k"] == "v"


# ---------------------------------------------------------------------------
# execute_prompt_chain_step
# ---------------------------------------------------------------------------


class TestExecutePromptChainStep:
    """Mock create_provider so the chain runs in-process with a fake LLM.

    The fake LLM returns a real AIMessage so JsonOutputParser and
    token_usage_from_aimessage exercise the real code paths.
    """

    def test_returns_parsed_pydantic_output(self, evaluation_metadata):
        from langchain_core.messages import AIMessage
        from langchain_core.prompts import ChatPromptTemplate

        def _fake_llm(prompt_value):
            return AIMessage(content=_CONV_JSON)

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with patch(_CHAIN_PATCH, return_value=_fake_llm):
            result = _evaluator().execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=ConventionalityOutput,
            )
        assert result.complexity_score == "slightly_complex"
        assert result.reasoning == "Clear."

    def test_prompt_settings_recorded_in_step_extras(self, evaluation_metadata):
        from langchain_core.messages import AIMessage
        from langchain_core.prompts import ChatPromptTemplate

        settings = PromptSettings(
            provider_type=LlmProvider.GOOGLE,
            model="gemini-2.0-flash",
            temperature=0.0,
        )
        template = ChatPromptTemplate.from_messages([("human", "{input}")])

        with patch(_CHAIN_PATCH, return_value=lambda pv: AIMessage(content=_CONV_JSON)):
            _evaluator().execute_prompt_chain_step(
                step_name="main",
                prompt_settings=settings,
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=ConventionalityOutput,
            )

        step = evaluation_metadata.step_details["main"]
        assert step.extras[PROMPT_STEP_EXTRA_PROMPT_SETTINGS]["model"] == "gemini-2.0-flash"
        assert PROMPT_STEP_EXTRA_TOKEN_USAGE in step.extras

    def test_token_usage_recorded_when_llm_reports_usage(self, evaluation_metadata):
        from langchain_core.messages import AIMessage
        from langchain_core.prompts import ChatPromptTemplate

        def _llm_with_usage(pv):
            return AIMessage(
                content=_CONV_JSON,
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
            _evaluator().execute_prompt_chain_step(
                step_name="main",
                prompt_settings=settings,
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=ConventionalityOutput,
            )

        step = evaluation_metadata.step_details["main"]
        assert step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE]["input_tokens"] == 42
        assert step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE]["output_tokens"] == 17
        assert evaluation_metadata.total_token_usage[LlmProvider.GOOGLE].input_tokens == 42

    def test_propagates_configuration_error_from_create_provider(self, evaluation_metadata):
        from langchain_core.prompts import ChatPromptTemplate

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(
                _CHAIN_PATCH,
                side_effect=ConfigurationError("Google provider config is not set"),
            ),
            pytest.raises(ConfigurationError, match="Google provider config is not set"),
        ):
            _evaluator().execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=ConventionalityOutput,
            )

    def test_wraps_unexpected_chain_failure_as_api_error(self, evaluation_metadata):
        """LangChain / provider failures are mapped via wrap_provider_error."""
        from langchain_core.prompts import ChatPromptTemplate

        def _boom(_prompt_value):
            raise ValueError("simulated provider failure")

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_boom),
            pytest.raises(APIError, match="simulated provider failure"),
        ):
            _evaluator().execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LlmProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=ConventionalityOutput,
            )
