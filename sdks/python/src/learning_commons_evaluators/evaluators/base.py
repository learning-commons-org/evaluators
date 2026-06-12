"""Base evaluator class. Config types live in schemas.config."""

from __future__ import annotations

import asyncio
import json as _json
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from typing import Any, Generic, TypeVar, overload

from langchain_core.exceptions import OutputParserException
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from learning_commons_evaluators.providers import (
    create_provider,
    token_usage_from_aimessage,
)
from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    EvaluatorConfig,
    PromptSettings,
)
from learning_commons_evaluators.schemas.errors import (
    EvaluatorError,
    OutputValidationError,
    format_error_for_metadata,
    sanitize_pydantic_errors,
    wrap_provider_error,
)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationInput,
    EvaluationResult,
)
from learning_commons_evaluators.schemas.llm_provider import (
    GenerateConfig,
    LLMGeneratorProtocol,
    LLMResponse,
)
from learning_commons_evaluators.schemas.metadata import (
    PROMPT_STEP_EXTRA_PROMPT_SETTINGS,
    PROMPT_STEP_EXTRA_TOKEN_USAGE,
    EvaluationMetadata,
    EvaluatorMetadata,
    Status,
    StepMetadata,
    TokenUsage,
    prompt_settings_to_extras_value,
)

# TypeVars used by module-level helpers and the BaseEvaluator generic class.
InputT = TypeVar("InputT", bound=EvaluationInput)
OutputT = TypeVar("OutputT", bound=EvaluationResult)
SettingsT = TypeVar("SettingsT", bound=EvaluationSettings)
StepResultT = TypeVar("StepResultT")
ParsedT = TypeVar("ParsedT", bound=BaseModel)


def _parse_json_output(
    raw: str,
    parser_output_type: type[ParsedT],
    json_dict_normalizer: Callable[[dict], dict] | None,
    provider_type: Any,
    model: str,
) -> ParsedT:
    """Parse a raw JSON string into ``parser_output_type``, wrapping errors consistently.

    Shared by both the protocol path and (for the normalizer branch) the LangChain path
    so that error handling is symmetric and normaliser logic lives in one place.
    """
    raw = _strip_json_fences(raw)
    try:
        if json_dict_normalizer is not None:
            parsed_dict = _json.loads(raw)
            if not isinstance(parsed_dict, dict):
                raise OutputValidationError(
                    "Model output is not a JSON object",
                    provider=provider_type,
                    model=model,
                )
            try:
                normalized = json_dict_normalizer(parsed_dict)
            except (TypeError, ValueError) as norm_err:
                raise OutputValidationError(
                    "Model output could not be normalized before validation",
                    provider=provider_type,
                    model=model,
                ) from norm_err
            return parser_output_type.model_validate(normalized)
        return parser_output_type.model_validate_json(raw)
    except PydanticValidationError as e:
        raise OutputValidationError(
            provider=provider_type,
            model=model,
            validation_errors=sanitize_pydantic_errors(e.errors()),
        ) from e
    except OutputValidationError:
        raise
    except Exception as e:
        raise OutputValidationError(provider=provider_type, model=model) from e


def _strip_json_fences(text: str) -> str:
    """Strip markdown code fences and extract the first valid JSON object or array.

    Uses ``json.JSONDecoder.raw_decode`` to locate the first balanced JSON structure
    and discard any surrounding prose or trailing text. This correctly handles:
    - Markdown-fenced responses: ````json\\n{...}\\n``` ``
    - Prose-prefixed responses: ``Here is the result:\\n{...}``
    - Trailing-prose responses: ``{...} Here is my reasoning...``
    """
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)
    text = text.strip()
    # Find the first { or [ and use raw_decode to extract the complete JSON structure,
    # correctly discarding any trailing prose or a second JSON object in the response.
    start = next((i for i, ch in enumerate(text) if ch in ("{", "[")), -1)
    if start != -1:
        try:
            _, end = _json.JSONDecoder().raw_decode(text, start)
            return text[start:end]
        except _json.JSONDecodeError:
            pass
    return text


class BaseEvaluator(ABC, Generic[InputT, OutputT, SettingsT]):
    """
    Abstract base class for all evaluators.
    Subclasses must set ``metadata``, ``default_evaluation_settings``, and implement
    :meth:`evaluate_impl`.

    Callers run an evaluation with :meth:`evaluate` (async: ``await evaluator.evaluate(...)``)
    or :meth:`evaluate_sync` from synchronous code (uses :func:`asyncio.run`). If a loop is
    already running on this thread, :meth:`evaluate_sync` raises :exc:`RuntimeError`; use
    ``await`` :meth:`evaluate` in that case.

    Pass ``default_evaluation_settings`` at construction to override the class-level
    defaults for that instance (used when :meth:`evaluate` is called without
    ``evaluation_settings``).
    """

    config: EvaluatorConfig
    metadata: EvaluatorMetadata
    default_evaluation_settings: SettingsT

    def __init__(
        self,
        config: EvaluatorConfig,
        *,
        llm_provider: LLMGeneratorProtocol | None = None,
        default_evaluation_settings: SettingsT | None = None,
    ) -> None:
        self.config = config
        self._llm_provider = llm_provider
        if default_evaluation_settings is not None:
            self.default_evaluation_settings = default_evaluation_settings
        # TODO: validate config

    async def evaluate(
        self,
        input: InputT,
        evaluation_settings: SettingsT | None = None,
    ) -> OutputT:
        """Evaluate the given input and return a structured result.

        Validates the input, delegates to :meth:`evaluate_impl`, records timing
        and status on the returned metadata, and logs start/end events via the
        configured logger. If ``evaluation_settings`` is ``None``, a deep copy of
        the instance's :attr:`default_evaluation_settings` is used (from the
        constructor keyword when given, otherwise the subclass class attribute).

        The ``finally`` block always runs so ``processing_time_ms`` and the end log
        line are emitted even when validation or the implementation raises; telemetry
        hooks remain TODOs here until wired.

        Args:
            input: Typed input for this evaluator.
            evaluation_settings: Optional override for evaluation settings.
                Defaults to :attr:`default_evaluation_settings` (constructor or class).

        Returns:
            A typed result whose ``metadata.status`` is
            :attr:`~learning_commons_evaluators.schemas.metadata.Status.succeeded`
            on success.

        Raises:
            InputValidationError: Input fails validation.
            ConfigurationError: No provider config for the required LLM provider.
            APIError (or subclasses): The LLM API call failed.

        On failure, :attr:`~learning_commons_evaluators.schemas.metadata.EvaluationMetadata.status`
        and ``error_details`` are set on the in-memory metadata object and included in the
        evaluation end log record; no result object is returned because this method re-raises.
        """
        if evaluation_settings is None:
            evaluation_settings = self.default_evaluation_settings.model_copy(deep=True)
        start = time.perf_counter()
        evaluation_metadata = EvaluationMetadata(
            evaluator_metadata=self.metadata,
            evaluation_settings=evaluation_settings,
            input_metadata=input.input_metadata(),
        )
        self.config.logger.info(
            "evaluation start",
            extra={"evaluation_metadata": evaluation_metadata},
        )
        try:
            input.validate()
            result = await self.evaluate_impl(input, evaluation_settings, evaluation_metadata)
            evaluation_metadata.status = Status.succeeded
            result.metadata = evaluation_metadata
            return result
        except Exception as e:
            evaluation_metadata.status = Status.failed
            evaluation_metadata.error_details = format_error_for_metadata(e)
            raise
        finally:
            evaluation_metadata.processing_time_ms = (time.perf_counter() - start) * 1000
            self.config.logger.info(
                "evaluation end",
                extra={"evaluation_metadata": evaluation_metadata},
            )
            # TODO: add full input to telemetry if enabled
            # TODO: send_telemetry(evaluation_metadata)

    def evaluate_sync(
        self,
        input: InputT,
        evaluation_settings: SettingsT | None = None,
    ) -> OutputT:
        """Run :meth:`evaluate` to completion from synchronous code.

        This is a thin wrapper around :func:`asyncio.run` over :meth:`evaluate`. Use it
        from scripts, REPLs, or tests that are not already inside an asyncio event loop.

        Args:
            input: Same as :meth:`evaluate`.
            evaluation_settings: Same as :meth:`evaluate`.

        Returns:
            Same typed result as :meth:`evaluate` on success.

        Raises:
            Same exceptions as :meth:`evaluate`.
            RuntimeError: If this thread already has a running asyncio event loop; use
                ``await evaluator.evaluate(...)`` instead of :meth:`evaluate_sync`.

        Note:
            Do not call this method when a running event loop is active (for example
            from inside an ``async def`` without nesting another ``asyncio.run``); prefer
            awaiting :meth:`evaluate` instead.
        """
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            pass
        else:
            raise RuntimeError(
                "evaluate_sync() cannot be used while an asyncio event loop is running in "
                "this thread; use await evaluator.evaluate(...) from async code instead."
            ) from None
        return asyncio.run(self.evaluate(input, evaluation_settings))

    @abstractmethod
    async def evaluate_impl(
        self,
        input: InputT,
        evaluation_settings: SettingsT,
        evaluation_metadata: EvaluationMetadata,
    ) -> OutputT:
        """Implement the evaluator-specific logic for one run.

        Subclasses perform prompt steps (often via :meth:`execute_prompt_chain_step`),
        assemble the typed result, and return it. The base :meth:`evaluate` assigns
        ``evaluation_metadata`` onto ``result.metadata`` after a successful return.

        Args:
            input: Validated evaluation input.
            evaluation_settings: Resolved settings for this run (already deep-copied
                when the caller omitted overrides).
            evaluation_metadata: Run metadata; populate ``step_details`` and related
                fields as steps execute.

        Returns:
            A fully constructed result object (``metadata`` may still point at the
            same ``evaluation_metadata`` instance; the base layer sets status and timing).
        """
        ...

    async def execute_step(
        self,
        step_name: str,
        evaluation_metadata: EvaluationMetadata,
        implementation_function: Callable[[], Awaitable[StepResultT]],
        *,
        extras: dict[str, Any] | None = None,
    ) -> StepResultT:
        """Await ``implementation_function`` and record step metadata on ``evaluation_metadata``.

        ``step_name`` is always the step id. Optional ``extras`` is copied into
        :attr:`StepMetadata.extras` (merged with any updates made during the step, e.g. token usage).

        ``implementation_function`` must be a zero-argument callable that returns an
        awaitable (typically an ``async def`` with no parameters, or a lambda that
        returns one). The awaited value may be any type (e.g. a Pydantic model, a plain
        ``str``, or ``None``); the same type is returned to the caller.
        """
        start = time.perf_counter()
        step_extras = dict(extras) if extras is not None else {}
        step_metadata = StepMetadata(step_id=step_name, extras=step_extras)
        self.config.logger.info("step start", extra={"step_metadata": step_metadata})
        try:
            result = await implementation_function()
            step_metadata.status = Status.succeeded
            return result
        except Exception as e:
            step_metadata.status = Status.failed
            step_metadata.error_details = format_error_for_metadata(e)
            raise
        finally:
            step_metadata.processing_time_ms = (time.perf_counter() - start) * 1000
            self.config.logger.info("step end", extra={"step_metadata": step_metadata})
            evaluation_metadata.step_details[step_name] = step_metadata

    @overload
    async def execute_prompt_chain_step(
        self,
        step_name: str,
        prompt_settings: PromptSettings,
        evaluation_metadata: EvaluationMetadata,
        template: Any,
        chain_inputs: dict[str, Any],
        parser_output_type: None = None,
    ) -> str: ...

    @overload
    async def execute_prompt_chain_step(
        self,
        step_name: str,
        prompt_settings: PromptSettings,
        evaluation_metadata: EvaluationMetadata,
        template: Any,
        chain_inputs: dict[str, Any],
        parser_output_type: type[ParsedT],
        json_dict_normalizer: Callable[[dict], dict] | None = None,
    ) -> ParsedT: ...

    async def execute_prompt_chain_step(
        self,
        step_name: str,
        prompt_settings: PromptSettings,
        evaluation_metadata: EvaluationMetadata,
        template: Any,
        chain_inputs: dict[str, Any],
        parser_output_type: type[BaseModel] | None = None,
        json_dict_normalizer: Callable[[dict], dict] | None = None,
    ) -> BaseModel | str:
        """Run a prompt chain (template | LLM) with ``ainvoke``, record metadata, and return the result.

        The LangChain runnable ``template | provider`` is invoked asynchronously via
        :meth:`~langchain_core.runnables.base.Runnable.ainvoke`. When ``parser_output_type``
        is a Pydantic model class, the LLM response is parsed as JSON and returned as an
        instance of that class. When it is ``None`` (the default), the raw response content
        is returned as a plain ``str`` (no JSON parser) — use that for steps that produce
        unstructured prose (e.g. a background-knowledge assumption).

        Provider config (e.g. API key) is resolved from ``self.config`` by
        ``prompt_settings.provider_type``.

        Args:
            step_name: Identifier for this step in ``evaluation_metadata.step_details``.
            prompt_settings: Provider type, model, and temperature for the LLM call.
            evaluation_metadata: Metadata for the full evaluation; step metadata and
                token usage are updated in place.
            template: A LangChain prompt template.
            chain_inputs: Variables to format the template and invoke the chain.
            parser_output_type: Pydantic model class for JSON parsing, or ``None``
                to return the raw text response.
            json_dict_normalizer: When set with ``parser_output_type``, parse the
                model response as JSON into a plain dict (no Pydantic parse),
                apply this function (e.g. notebook-style ``normalize_complexity_output``),
                then validate with ``parser_output_type``. Format instructions for the
                prompt should still be built from the same ``parser_output_type`` via
                :class:`~langchain_core.output_parsers.JsonOutputParser`.

        Returns:
            Parsed instance of ``parser_output_type`` when it is a model class; plain
            ``str`` when ``parser_output_type`` is omitted or ``None``.

        Note:
            **Execution path**: when ``self._llm_provider`` is set (injected at
            construction via ``BaseEvaluator.__init__``), the *protocol path* is taken
            — the LangChain template is formatted to extract system/human strings, the
            injected provider is called directly, and JSON is parsed via Pydantic.
            When ``self._llm_provider`` is ``None`` (default), the *LangChain path*
            is taken and ``create_provider()`` is called internally.

        Raises:
            ConfigurationError: No provider config for ``prompt_settings.provider_type``.
            OutputValidationError: The LLM response didn't satisfy the expected
                output schema — invalid JSON (LangChain ``OutputParserException``),
                JSON that didn't match the Pydantic model (``pydantic.ValidationError``),
                a non-object JSON value when using ``json_dict_normalizer``, or
                ``TypeError`` / ``ValueError`` from ``json_dict_normalizer`` itself.
                The original exception is reachable via ``__cause__``.
            APIError (or other ``EvaluatorError`` subclasses):
                :func:`~learning_commons_evaluators.schemas.errors.wrap_provider_error`
                output for LangChain or HTTP failures from the LLM provider.
            ValueError: If ``json_dict_normalizer`` is set but ``parser_output_type`` is omitted.
        """
        if json_dict_normalizer is not None and parser_output_type is None:
            raise ValueError("json_dict_normalizer requires parser_output_type to be set")
        # Populated after a successful LLM invoke so we can attach usage even if parsing fails.
        token_usage: TokenUsage | None = None

        if self._llm_provider is not None:
            # ── Protocol path ──────────────────────────────────────────────
            # Format the LangChain template to extract system/human strings,
            # then delegate the actual LLM call to the injected provider.
            # JSON parsing is handled directly via Pydantic — no LangChain parser needed.
            provider = self._llm_provider

            async def _run_via_provider() -> BaseModel | str:
                nonlocal token_usage
                try:
                    # Template formatting is inside try so missing variables become EvaluatorErrors,
                    # not bare KeyErrors — matching the error contract of the LangChain path.
                    formatted = await template.aformat_messages(**chain_inputs)
                    system_str = next(
                        (str(m.content) for m in formatted if getattr(m, "type", "") == "system"),
                        "",
                    )
                    human_str = next(
                        (str(m.content) for m in formatted if getattr(m, "type", "") == "human"),
                        "",
                    )
                    if not human_str:
                        raise ValueError(
                            f"Template for step '{step_name}' produced no human message. "
                            'Ensure the template contains at least one ("human", ...) turn.'
                        )
                    if not system_str:
                        self.config.logger.debug(
                            "No system message in template for step '%s'; "
                            "passing empty string to adapter.",
                            step_name,
                        )
                    response: LLMResponse = await provider.generate(
                        system=system_str,
                        human=human_str,
                        config=GenerateConfig(
                            temperature=prompt_settings.temperature,
                            model=prompt_settings.model,
                        ),
                    )
                except EvaluatorError:
                    raise
                except (KeyboardInterrupt, SystemExit):
                    raise
                except Exception as e:
                    raise wrap_provider_error(
                        e,
                        provider=prompt_settings.provider_type,
                        model=prompt_settings.model,
                    ) from e
                if response.input_tokens is not None or response.output_tokens is not None:
                    token_usage = TokenUsage(
                        provider_type=prompt_settings.provider_type,
                        model=response.model,
                        input_tokens=response.input_tokens or 0,
                        output_tokens=response.output_tokens or 0,
                    )
                if parser_output_type is None:
                    return response.content
                return _parse_json_output(
                    response.content,
                    parser_output_type,
                    json_dict_normalizer,
                    prompt_settings.provider_type,
                    response.model,
                )

            try:
                return await self.execute_step(
                    step_name,
                    evaluation_metadata,
                    _run_via_provider,
                    extras={
                        PROMPT_STEP_EXTRA_PROMPT_SETTINGS: prompt_settings_to_extras_value(
                            prompt_settings
                        ),
                    },
                )
            finally:
                if token_usage is not None:
                    self.update_total_token_usage(token_usage, evaluation_metadata)
                    step = evaluation_metadata.step_details.get(step_name)
                    if step is not None:
                        step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE] = token_usage.model_dump(
                            mode="json"
                        )

        # ── LangChain path (default, unchanged) ───────────────────────────
        async def _run_chain() -> BaseModel | str:
            nonlocal token_usage
            try:
                provider = create_provider(prompt_settings, self.config)
                llm_chain: Any = template | provider
                ai_message = await llm_chain.ainvoke(chain_inputs)
                token_usage = token_usage_from_aimessage(ai_message, prompt_settings)
                if parser_output_type is None:
                    return str(ai_message.content)
                from langchain_core.output_parsers.json import JsonOutputParser

                if json_dict_normalizer is not None:
                    # Use the shared helper so normalizer + error-wrapping logic stays in one place.
                    return _parse_json_output(
                        str(ai_message.content),
                        parser_output_type,
                        json_dict_normalizer,
                        prompt_settings.provider_type,
                        prompt_settings.model,
                    )

                parser = JsonOutputParser(pydantic_object=parser_output_type)
                raw = await parser.ainvoke(ai_message)
                if isinstance(raw, parser_output_type):
                    return raw
                return parser_output_type.model_validate(raw)
            except EvaluatorError:
                raise
            except (PydanticValidationError, OutputParserException) as e:
                # The provider returned a response that didn't match the expected schema.
                # This covers both Pydantic schema-validation failures and LangChain
                # JSON-parse failures (``OutputParserException``). Wrap so callers can
                # discriminate output-parse failures from other API errors and so the
                # message that lands in ``EvaluationMetadata.error_details`` stays
                # sanitized — the original error (which may include LLM output snippets)
                # is reachable via ``__cause__`` for debugging.
                validation_errors = (
                    sanitize_pydantic_errors(e.errors())
                    if isinstance(e, PydanticValidationError)
                    else None
                )
                raise OutputValidationError(
                    provider=prompt_settings.provider_type,
                    model=prompt_settings.model,
                    validation_errors=validation_errors,
                ) from e
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception as e:
                raise wrap_provider_error(
                    e,
                    provider=prompt_settings.provider_type,
                    model=prompt_settings.model,
                ) from e

        try:
            return await self.execute_step(
                step_name,
                evaluation_metadata,
                _run_chain,
                extras={
                    PROMPT_STEP_EXTRA_PROMPT_SETTINGS: prompt_settings_to_extras_value(
                        prompt_settings
                    ),
                },
            )
        finally:
            if token_usage is not None:
                self.update_total_token_usage(token_usage, evaluation_metadata)
                step = evaluation_metadata.step_details.get(step_name)
                if step is not None:
                    step.extras[PROMPT_STEP_EXTRA_TOKEN_USAGE] = token_usage.model_dump(mode="json")

    def update_total_token_usage(
        self, token_usage: TokenUsage, evaluation_metadata: EvaluationMetadata
    ) -> None:
        """Record token usage for the current run."""
        if token_usage.provider_type not in evaluation_metadata.total_token_usage:
            evaluation_metadata.total_token_usage[token_usage.provider_type] = token_usage
        else:
            current_total = evaluation_metadata.total_token_usage[token_usage.provider_type]
            evaluation_metadata.total_token_usage[token_usage.provider_type] = TokenUsage(
                provider_type=current_total.provider_type,
                model=current_total.model,
                input_tokens=current_total.input_tokens + token_usage.input_tokens,
                output_tokens=current_total.output_tokens + token_usage.output_tokens,
            )
