"""Tests for :class:`~learning_commons_evaluators.evaluators.base.BaseEvaluator`.

Covers ``__init__``, ``evaluate`` / ``evaluate_sync``, metadata and settings override,
success/failure paths, ``update_total_token_usage``, ``execute_step``, and
``execute_prompt_chain_step``.
``EvaluationMetadata`` always uses ``input.input_metadata()`` (including when
``send_full_input_with_telemetry`` is enabled). Helpers use both a minimal stub evaluator
and conventionality-oriented fixtures where useful.
"""

from __future__ import annotations

import logging
from typing import NoReturn
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from typing_extensions import override

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
    LLMProvider,
    PromptSettings,
)
from learning_commons_evaluators.schemas.errors import (
    APIError,
    EvaluatorError,
    InputValidationError,
    OutputValidationError,
)
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


def _fake_chat_model(message: AIMessage) -> FakeMessagesListChatModel:
    """Fixed-response chat model for ``template | model`` chains (MagicMock breaks LC compose)."""

    return FakeMessagesListChatModel(responses=[message])


class _ChainFailureChatModel(BaseChatModel):
    """Chat model that always raises inside generation (provider failure simulation)."""

    @override
    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: CallbackManagerForLLMRun | None = None,
        **kwargs: object,
    ) -> NoReturn:
        raise ValueError("simulated provider failure")

    @property
    @override
    def _llm_type(self) -> str:
        return "chain-failure-test-double"


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

    async def evaluate_impl(
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

    def test_constructor_default_evaluation_settings_overrides_class_default(self, config):
        instance_default = _StubSettings(marker=99)
        ev = _StubEvaluator(config, default_evaluation_settings=instance_default)
        assert ev.default_evaluation_settings is instance_default

    def test_omitted_constructor_default_falls_back_to_class_attribute(self, config):
        ev = _StubEvaluator(config)
        assert ev.default_evaluation_settings is _StubEvaluator.default_evaluation_settings


# ---------------------------------------------------------------------------
# evaluate()
# ---------------------------------------------------------------------------


class TestEvaluateSuccess:
    def test_sets_status_succeeded_and_processing_time(self, stub_evaluator):
        result = stub_evaluator.evaluate_sync(_stub_input())
        assert result.metadata.status == Status.succeeded
        assert result.metadata.processing_time_ms >= 0.0

    def test_passes_explicit_evaluation_settings(self, stub_evaluator):
        custom = _StubSettings(marker=42)
        result = stub_evaluator.evaluate_sync(_stub_input(), evaluation_settings=custom)
        assert result.metadata.evaluation_settings.marker == 42
        assert result.explanation.details.get("marker") == 42

    def test_constructor_default_used_when_evaluate_settings_omitted(self, config):
        ev = _StubEvaluator(config, default_evaluation_settings=_StubSettings(marker=77))
        result = ev.evaluate_sync(_stub_input())
        assert result.metadata.evaluation_settings.marker == 77
        assert result.explanation.details.get("marker") == 77

    def test_evaluate_explicit_settings_override_constructor_default(self, config):
        ev = _StubEvaluator(
            config,
            default_evaluation_settings=_StubSettings(marker=1),
        )
        result = ev.evaluate_sync(_stub_input(), evaluation_settings=_StubSettings(marker=2))
        assert result.explanation.details.get("marker") == 2


class TestEvaluateSyncLoopGuard:
    @pytest.mark.asyncio
    async def test_evaluate_sync_raises_clear_error_when_loop_running(self, stub_evaluator):
        with pytest.raises(RuntimeError, match="await evaluator.evaluate"):
            stub_evaluator.evaluate_sync(_stub_input())


class TestEvaluateAsyncEntrypoint:
    """``await evaluator.evaluate(...)`` is the primary API when an event loop is already running."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_result_in_async_context(self, stub_evaluator):
        result = await stub_evaluator.evaluate(_stub_input())
        assert result.metadata.status == Status.succeeded
        assert result.metadata.processing_time_ms >= 0.0


class TestEvaluateInputMetadata:
    """``input_metadata`` on :class:`EvaluationMetadata` always comes from ``input.input_metadata()``."""

    def test_evaluate_sets_metadata_from_input_metadata(self, stub_evaluator):
        inp = _stub_input()
        result = stub_evaluator.evaluate_sync(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": 11}
        assert result.metadata.input_metadata["grade_level"] == {"grade": 3}

    def test_full_telemetry_config_still_uses_input_metadata_not_raw_values(self, stub_evaluator):
        """``send_full_input_with_telemetry`` does not replace ``input_metadata`` with raw values."""
        cfg = create_config(telemetry_partner_id="test", send_full_input_with_telemetry=True)
        ev = _StubEvaluator(cfg)
        inp = _stub_input()
        result = ev.evaluate_sync(inp)
        assert result.metadata.input_metadata == inp.input_metadata()
        assert result.metadata.input_metadata["text"] == {"textLength": 11}
        assert result.metadata.input_metadata["grade_level"] == {"grade": 3}


class TestStubEvaluateErrorHandling:
    def test_raises_validation_error_for_invalid_input(self, stub_evaluator):
        inp = TextComplexityEvaluationInput(
            text=TextInputField(
                spec=TextInputSpec(name="text", min_text_length=100),
                value="short",
            ),
            grade_level=GradeInputField(spec=GradeInputSpec(name="grade_level"), value=3),
        )
        with pytest.raises(InputValidationError):
            stub_evaluator.evaluate_sync(inp)

    def test_propagates_evaluate_impl_exception(self, stub_evaluator):
        with (
            patch.object(
                stub_evaluator, "evaluate_impl", AsyncMock(side_effect=RuntimeError("boom"))
            ),
            pytest.raises(RuntimeError, match="boom"),
        ):
            stub_evaluator.evaluate_sync(_stub_input())

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
            with pytest.raises(InputValidationError):
                stub_evaluator.evaluate_sync(inp)
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
            provider_type=LLMProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        stub_evaluator.update_total_token_usage(usage, evaluation_metadata)
        stored = evaluation_metadata.total_token_usage[LLMProvider.GOOGLE]
        assert stored.input_tokens == 10
        assert stored.output_tokens == 5

    def test_accumulates_usage_for_existing_provider(self, stub_evaluator, evaluation_metadata):
        evaluation_metadata.total_token_usage[LLMProvider.GOOGLE] = TokenUsage(
            provider_type=LLMProvider.GOOGLE,
            model="gemini-2.0-flash",
            input_tokens=10,
            output_tokens=5,
        )
        stub_evaluator.update_total_token_usage(
            TokenUsage(
                provider_type=LLMProvider.GOOGLE,
                model="gemini-2.0-flash",
                input_tokens=20,
                output_tokens=15,
            ),
            evaluation_metadata,
        )
        stored = evaluation_metadata.total_token_usage[LLMProvider.GOOGLE]
        assert stored.input_tokens == 30
        assert stored.output_tokens == 20


# ---------------------------------------------------------------------------
# execute_step
# ---------------------------------------------------------------------------


class TestExecuteStep:
    async def test_returns_implementation_result(self, stub_evaluator, evaluation_metadata):
        async def impl():
            return "the-result"

        assert await stub_evaluator.execute_step("s", evaluation_metadata, impl) == "the-result"

    async def test_records_succeeded_status_on_success(self, stub_evaluator, evaluation_metadata):
        async def impl():
            return None

        await stub_evaluator.execute_step("s", evaluation_metadata, impl)
        assert evaluation_metadata.step_details["s"].status == Status.succeeded

    async def test_records_failed_status_and_sanitized_error_on_unexpected_exception(
        self, stub_evaluator, evaluation_metadata
    ):
        """Non-SDK exceptions record only the class name in step metadata.

        The raw message (``"boom"`` here) is intentionally stripped — for arbitrary
        exceptions the message may contain user data, prompt content, or field values
        that aren't safe for logs/telemetry. The exception itself still propagates
        unchanged for callers that catch it.
        """

        async def failing():
            raise ValueError("boom with possibly-sensitive context")

        with pytest.raises(ValueError, match="boom"):
            await stub_evaluator.execute_step("s", evaluation_metadata, failing)
        step = evaluation_metadata.step_details["s"]
        assert step.status == Status.failed
        # Class name is included; raw message is not.
        assert "ValueError" in step.error_details
        assert "boom" not in step.error_details

    async def test_records_failed_status_and_sanitized_error_on_sdk_exception(
        self, stub_evaluator, evaluation_metadata
    ):
        """SDK exceptions land in step metadata as ``ClassName: <sanitized message>``."""

        async def failing():
            raise InputValidationError("text length 3 below minimum 10")

        with pytest.raises(InputValidationError):
            await stub_evaluator.execute_step("s", evaluation_metadata, failing)
        step = evaluation_metadata.step_details["s"]
        assert step.status == Status.failed
        # SDK error messages are already controlled by us, so they're included verbatim.
        assert step.error_details == "InputValidationError: text length 3 below minimum 10"

    async def test_re_raises_exception(self, stub_evaluator, evaluation_metadata):
        async def failing():
            raise RuntimeError("inner")

        with pytest.raises(RuntimeError, match="inner"):
            await stub_evaluator.execute_step("s", evaluation_metadata, failing)

    async def test_extras_appear_in_step_metadata(self, stub_evaluator, evaluation_metadata):
        async def impl():
            return None

        await stub_evaluator.execute_step("s", evaluation_metadata, impl, extras={"k": "v"})
        assert evaluation_metadata.step_details["s"].extras["k"] == "v"


# ---------------------------------------------------------------------------
# execute_prompt_chain_step
# ---------------------------------------------------------------------------


class TestExecutePromptChainStep:
    """Mock ``create_provider`` so ``template | provider`` runs in-process."""

    async def test_returns_raw_string_when_parser_output_type_is_none(
        self, stub_evaluator, evaluation_metadata
    ):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        ev = _StubEvaluator(create_config_no_telemetry())
        with patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content="plain prose"))):
            out = await ev.execute_prompt_chain_step(
                step_name="raw",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=None,
            )
        assert out == "plain prose"

    async def test_json_dict_normalizer_without_parser_type_raises(
        self, stub_evaluator, evaluation_metadata
    ):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with pytest.raises(ValueError, match="json_dict_normalizer requires"):
            await stub_evaluator.execute_prompt_chain_step(
                step_name="raw",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=None,
                json_dict_normalizer=lambda d: d,
            )

    async def test_returns_parsed_pydantic_output(self, stub_evaluator, evaluation_metadata):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content=_CHAIN_JSON))):
            result = await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
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

    async def test_json_dict_normalizer_parses_dict_then_normalizes_then_validates(
        self, stub_evaluator, evaluation_metadata
    ):
        """Optional ``json_dict_normalizer``: loose JSON → dict → user fn → ``model_validate``."""

        class _Out(BaseModel):
            n: int = Field(description="n")
            doubled: int = Field(description="doubled")

        def _double(d: dict) -> dict:
            d = dict(d)
            d["doubled"] = int(d["n"]) * 2
            return d

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with patch(
            _CHAIN_PATCH,
            return_value=_fake_chat_model(AIMessage(content='{"n": 1}')),
        ):
            result = await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=_Out,
                json_dict_normalizer=_double,
            )
        assert isinstance(result, _Out)
        assert result.n == 1
        assert result.doubled == 2

    async def test_parser_returning_model_instance_short_circuits_model_validate(
        self, stub_evaluator, evaluation_metadata
    ):
        """When ``JsonOutputParser.ainvoke`` returns a model, ``isinstance`` path skips ``model_validate``."""
        prebuilt = _ChainOutput(label="direct", score=99)

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content="unused"))),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.return_value = prebuilt
            mock_parser.ainvoke = AsyncMock(return_value=prebuilt)
            mock_parser_cls.return_value = mock_parser
            result = await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "Hello"},
                parser_output_type=_ChainOutput,
            )
        assert result is prebuilt

    async def test_keyboard_interrupt_from_parser_propagates(
        self, stub_evaluator, evaluation_metadata
    ):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content=_CHAIN_JSON))),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.side_effect = KeyboardInterrupt
            mock_parser.ainvoke = AsyncMock(side_effect=KeyboardInterrupt)
            mock_parser_cls.return_value = mock_parser
            with pytest.raises(KeyboardInterrupt):
                await stub_evaluator.execute_prompt_chain_step(
                    step_name="main",
                    prompt_settings=PromptSettings(
                        provider_type=LLMProvider.GOOGLE,
                        model="gemini-2.0-flash",
                        temperature=0.0,
                    ),
                    evaluation_metadata=evaluation_metadata,
                    template=template,
                    chain_inputs={"input": "Hello"},
                    parser_output_type=_ChainOutput,
                )

    async def test_system_exit_from_parser_propagates(self, stub_evaluator, evaluation_metadata):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content=_CHAIN_JSON))),
            patch("langchain_core.output_parsers.json.JsonOutputParser") as mock_parser_cls,
        ):
            mock_parser = MagicMock()
            mock_parser.invoke.side_effect = SystemExit(3)
            mock_parser.ainvoke = AsyncMock(side_effect=SystemExit(3))
            mock_parser_cls.return_value = mock_parser
            with pytest.raises(SystemExit) as exc_info:
                await stub_evaluator.execute_prompt_chain_step(
                    step_name="main",
                    prompt_settings=PromptSettings(
                        provider_type=LLMProvider.GOOGLE,
                        model="gemini-2.0-flash",
                        temperature=0.0,
                    ),
                    evaluation_metadata=evaluation_metadata,
                    template=template,
                    chain_inputs={"input": "Hello"},
                    parser_output_type=_ChainOutput,
                )
            assert exc_info.value.code == 3

    async def test_prompt_settings_recorded_in_step_extras(
        self, stub_evaluator, evaluation_metadata
    ):
        settings = PromptSettings(
            provider_type=LLMProvider.GOOGLE,
            model="gemini-2.0-flash",
            temperature=0.0,
        )
        template = ChatPromptTemplate.from_messages([("human", "{input}")])

        with patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content=_CHAIN_JSON))):
            await stub_evaluator.execute_prompt_chain_step(
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

    async def test_token_usage_recorded_when_llm_reports_usage(
        self, stub_evaluator, evaluation_metadata
    ):
        msg = AIMessage(
            content=_CHAIN_JSON,
            usage_metadata={
                "input_tokens": 42,
                "output_tokens": 17,
                "total_tokens": 59,
            },
        )

        settings = PromptSettings(
            provider_type=LLMProvider.GOOGLE,
            model="gemini-2.0-flash",
            temperature=0.0,
        )
        template = ChatPromptTemplate.from_messages([("human", "{input}")])

        with patch(_CHAIN_PATCH, return_value=_fake_chat_model(msg)):
            await stub_evaluator.execute_prompt_chain_step(
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
        assert evaluation_metadata.total_token_usage[LLMProvider.GOOGLE].input_tokens == 42

    async def test_propagates_configuration_error_from_create_provider(
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
            await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    async def test_propagates_evaluator_error_without_wrapping(
        self, stub_evaluator, evaluation_metadata
    ):
        """``EvaluatorError`` subclasses raised inside the chain are re-raised unchanged."""
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, side_effect=EvaluatorError("bare evaluator error")),
            pytest.raises(EvaluatorError, match="bare evaluator error"),
        ):
            await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )

    async def test_wraps_unexpected_chain_failure_as_api_error(
        self, stub_evaluator, evaluation_metadata
    ):
        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(_CHAIN_PATCH, return_value=_ChainFailureChatModel()),
            pytest.raises(APIError, match="^API request failed$") as exc_info,
        ):
            await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )
        cause = exc_info.value.__cause__
        assert isinstance(cause, ValueError)
        assert str(cause) == "simulated provider failure"

    async def test_malformed_llm_json_raises_output_validation_error(
        self, stub_evaluator, evaluation_metadata
    ):
        """Invalid JSON from the LLM becomes :class:`OutputValidationError` (a subclass of APIError).

        LangChain raises ``OutputParserException`` for unparseable JSON; we wrap it so the
        SDK exposes a single, sanitized parse-failure type instead of leaking the raw
        ``"Invalid json output: <model text>"`` string (which would echo LLM content).
        """

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        bad_output = "not-json with prompt echo: API_KEY=sk-...REDACTED"
        with (
            patch(_CHAIN_PATCH, return_value=_fake_chat_model(AIMessage(content=bad_output))),
            pytest.raises(OutputValidationError) as exc_info,
        ):
            await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )
        # Sanitized — the raw model output must not appear in str() of the wrapped error.
        assert "API_KEY" not in str(exc_info.value)
        assert "sk-" not in str(exc_info.value)
        # Original exception is preserved for debugging.
        assert exc_info.value.__cause__ is not None
        # Subclass relationship: callers can still catch APIError.
        assert isinstance(exc_info.value, APIError)
        # Provider/model context is threaded through.
        assert exc_info.value.provider is LLMProvider.GOOGLE
        assert exc_info.value.model == "gemini-2.0-flash"

    async def test_schema_mismatch_raises_output_validation_error(
        self, stub_evaluator, evaluation_metadata
    ):
        """Valid JSON that doesn't satisfy the output model becomes :class:`OutputValidationError`.

        Pydantic's :class:`ValidationError` is wrapped so the original (which may
        include input value snippets via Pydantic's default formatting) stays on
        ``__cause__`` rather than the SDK error's ``str()``. The structured
        per-field details land on ``validation_errors`` with input values stripped.
        """

        template = ChatPromptTemplate.from_messages([("human", "{input}")])
        with (
            patch(
                _CHAIN_PATCH,
                return_value=_fake_chat_model(AIMessage(content='{"label": "only"}')),
            ),
            pytest.raises(OutputValidationError) as exc_info,
        ):
            await stub_evaluator.execute_prompt_chain_step(
                step_name="main",
                prompt_settings=PromptSettings(
                    provider_type=LLMProvider.GOOGLE,
                    model="gemini-2.0-flash",
                    temperature=0.0,
                ),
                evaluation_metadata=evaluation_metadata,
                template=template,
                chain_inputs={"input": "text"},
                parser_output_type=_ChainOutput,
            )
        # Pydantic error preserved for callers that want full detail.
        assert isinstance(exc_info.value.__cause__, PydanticValidationError)
        # Structured per-field errors are populated; raw 'input' is stripped.
        assert exc_info.value.validation_errors is not None
        assert len(exc_info.value.validation_errors) > 0
        for entry in exc_info.value.validation_errors:
            assert "input" not in entry
            assert "loc" in entry
            assert "type" in entry
