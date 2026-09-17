"""The evaluator for a contract with one model call.

The flow — validate, preprocess, render, call, envelope, error wrap — is written once
here. A concrete evaluator is a declaration::

    class PurposeClarityEvaluator(SingleStepEvaluator[PurposeClarityInput, PurposeClarityOutput]):
        contract = load_contract("student_facing_text.ela_reading.purpose_clarity")
        input_model = PurposeClarityInput
        output_model = PurposeClarityOutput

Everything that varies is read from the contract at class creation, so an evaluator
cannot drift from what its contract declares, and a contract this class cannot run fails
at import rather than on the first evaluation. This is the Python form of the TypeScript
SDK's ``defineSingleStepEvaluator`` factory.
"""

from __future__ import annotations

import time
from collections.abc import Mapping
from typing import Any, ClassVar, Generic, TypeVar, cast

from pydantic import BaseModel

from learning_commons_evaluators.contracts.loader import Contract, Preprocessing, Step
from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.inputs import primary_text_field, validate_inputs
from learning_commons_evaluators.features.preprocessing import (
    check_implementation,
    format_number,
    run_preprocessing_step,
)
from learning_commons_evaluators.prompts.render import render_prompt
from learning_commons_evaluators.providers import (
    LLMProvider,
    Message,
    Provider,
    call_with_resampling,
    provider_context,
)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
)
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


def step_for(contract: Contract) -> Step:
    """The step the convention names: ``evaluate_{slug}``, where slug is the id's last segment."""
    return contract.step(f"evaluate_{contract.evaluator.slug}")


class SingleStepEvaluator(BaseEvaluator, Generic[InputT, OutputT]):
    """Base for every evaluator whose contract declares one LLM step."""

    #: The declarations a concrete class makes, alongside ``contract`` from the base.
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]

    # Resolved from the contract at class creation.
    _step: ClassVar[Step]
    _vendor: ClassVar[Provider]
    _preprocessing: ClassVar[tuple[Preprocessing, ...]]
    _text_field: ClassVar[str | None]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "contract"):
            return  # an abstract intermediate; the declaring subclass resolves
        contract = cls.contract
        name = contract.evaluator.name

        # Exactly one step, and not an optional one: this base runs the step the convention
        # names and nothing else, so any other step would be silently skipped while the
        # metadata and credential checks described the whole contract.
        if len(contract.steps) != 1 or contract.steps[0].optional:
            raise ValueError(
                f"{name} config.json declares {len(contract.steps)} step(s); SingleStepEvaluator "
                "runs exactly one non-optional step. Use the multi-step base."
            )
        step = step_for(contract)
        if step.type != "llm" or step.prompt is None or step.model is None:
            raise ValueError(f'Step "{step.id}" in {name} config.json is not an LLM step.')
        for placeholder, declared in step.prompt.placeholders.items():
            if declared.source.startswith("steps."):
                raise ValueError(
                    f'Placeholder "{placeholder}" in {name} reads another step; '
                    "a single-step evaluator has none. Use the multi-step base."
                )

        for entry in contract.preprocessing:
            if entry.type != "computation" or entry.python is None:
                raise ValueError(
                    f'Preprocessing "{entry.id}" in {name} config.json declares no Python '
                    "computation this evaluator can run."
                )
            # A library or transform this SDK lacks is our gap, not the provider's: fail
            # here, at import, rather than inside the evaluation's error boundary.
            try:
                check_implementation(entry.python)
            except NotImplementedError as gap:
                raise NotImplementedError(
                    f'Preprocessing "{entry.id}" in {name} config.json: {gap}'
                ) from None

        cls._step = step
        cls._vendor = step.model.provider
        cls._preprocessing = tuple(contract.preprocessing)
        cls._text_field = primary_text_field(contract.input_schema)
        cls.metadata = EvaluatorMetadata.from_contract(contract, (step.model.provider,))

    def __init__(self, config: Any = None, /, **fields: Any) -> None:
        super().__init__(config, **fields)
        assert self._step.model is not None  # established at class creation
        self.provider: LLMProvider = self._create_configured_provider(
            self._vendor, self._step.model.name
        )

    async def evaluate(
        self, input: InputT | None = None, /, **fields: Any
    ) -> EvaluationResult[OutputT]:
        """Evaluate the contract's inputs, passed as the typed input model or by name.

        :raises InputValidationError: an input is missing, unknown, or outside its schema.
        :raises ConfigurationError: the provider rejected the configured model id, or a
            required placeholder has no value from the source the contract names.
        :raises DependencyError: the provider call failed (``AuthenticationError``,
            ``RateLimitError``, ``NetworkError``, ``RequestTimeoutError``, ``LLMProviderError``).
        :raises LLMOutputProcessingError: the model's response failed its output schema
            after ``max_retries`` immediate resamples.
        """
        start = time.perf_counter()
        context = {"evaluator": self.metadata.id, "operation": "evaluate"}
        grade_level = ""
        # Argument shape is a programmer error, raised as such; everything from validation
        # on is an evaluation failure, logged and classified.
        raw = self._raw_fields(input, fields)
        try:
            values = validate_inputs(raw, self.contract.input_schema)
            text = values.get(self._text_field, "") if self._text_field else ""
            grade_level = values.get("grade_level", "")
            self.logger.info(
                "Starting %s evaluation",
                self.metadata.label,
                extra={**context, "grade_level": grade_level, "text_length": len(text)},
            )

            messages = self._render_messages(values)
            dependency, model = provider_context(self.provider)
            assert self._step.model is not None
            response = await call_with_resampling(
                lambda: self.provider.generate_structured(
                    messages,
                    self.output_model,
                    temperature=self.effective_temperature(self._step.temperature),
                ),
                max_retries=self.config.max_retries,
                dependency=dependency,
                model=model,
                logger=self.logger,
            )

            elapsed_ms = int((time.perf_counter() - start) * 1000)
            result: EvaluationResult[Any] = EvaluationResult(
                evaluator=self.metadata.id,
                result=response.data,
                metadata=EvaluationMetadata(
                    model=self.provider.label,
                    processing_time_ms=elapsed_ms,
                    token_usage=EvaluationTokenUsage(
                        input_tokens=response.usage.input_tokens,
                        output_tokens=response.usage.output_tokens,
                    ),
                ),
            )
            outcome = self.metadata.outcome
            self.logger.info(
                "%s evaluation completed successfully",
                self.metadata.label,
                extra={
                    **context,
                    "grade_level": grade_level,
                    "score": getattr(response.data, outcome.score, None) if outcome else None,
                    "processing_time_ms": elapsed_ms,
                },
            )
            return cast(EvaluationResult[OutputT], result)
        except Exception as error:
            elapsed_ms = int((time.perf_counter() - start) * 1000)
            self.logger.error(
                "%s evaluation failed",
                self.metadata.label,
                extra={
                    **context,
                    "grade_level": grade_level,
                    "error": type(error).__name__,
                    "processing_time_ms": elapsed_ms,
                },
            )
            # Nothing is re-classified here. Every provider failure was already mapped by
            # ``call_with_resampling``; anything else reaching this point is a fault in this
            # SDK, and wrapping it as a provider error would name a service that did not
            # fail (spec §6.2) and hide the bug.
            raise

    # --- pieces of the flow ------------------------------------------------------------

    def _prompt_inputs(self, values: Mapping[str, str]) -> dict[str, str]:
        """Every placeholder the step declares, resolved from the source the contract names."""
        computed: dict[str, str] = {}
        for entry in self._preprocessing:
            if entry.condition is not None and not entry.condition.holds(dict(values)):
                continue
            assert entry.python is not None and entry.output is not None
            source = values.get(entry.input or "", "")
            computed[entry.output] = format_number(run_preprocessing_step(source, entry.python))

        assert self._step.prompt is not None
        inputs: dict[str, str] = {}
        for name, placeholder in self._step.prompt.placeholders.items():
            kind, _, rest = placeholder.source.partition(".")
            if placeholder.source == "input":
                value = values.get(name)
            elif kind == "input":
                value = values.get(rest)
            else:  # preprocessing.<output>
                value = computed.get(rest)
            if value is None:
                if placeholder.required:
                    # The contract's own inconsistency, not a service's: registry data is
                    # the caller's fault domain (spec §6.1), and stamping a provider on it
                    # would name a dependency that did not fail (§6.2).
                    raise ConfigurationError(
                        f'Placeholder "{name}" in {self.metadata.name} has no value '
                        f"from source {placeholder.source!r}."
                    )
                continue
            inputs[name] = value
        return inputs

    def _render_messages(self, values: Mapping[str, str]) -> list[Message]:
        assert self._step.prompt is not None
        inputs = self._prompt_inputs(values)
        placeholders = list(self._step.prompt.placeholders)
        return [
            Message(
                role=message.role,
                content=render_prompt(
                    self.contract.document(message.source_path), inputs, placeholders
                ),
            )
            for message in self._step.prompt.messages
        ]


__all__ = ["SingleStepEvaluator", "step_for"]
