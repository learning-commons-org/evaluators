"""The evaluator for a contract with one model call.

The flow — validate, preprocess, render, call, envelope, error wrap — is written once
here. A concrete evaluator is a declaration::

    class PurposeClarityEvaluator(SingleStepEvaluator[PurposeClarityInput, PurposeClarityOutput]):
        contract = load_contract("text_complexity.ela_reading.purpose_clarity")
        input_model = PurposeClarityInput
        output_model = PurposeClarityOutput

Everything that varies is read from the contract at class creation, so an evaluator
cannot drift from what its contract declares, and a contract this class cannot run fails
at import rather than on the first evaluation. This is the Python form of the TypeScript
SDK's ``defineSingleStepEvaluator`` factory.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, NoReturn, TypeGuard, TypeVar, cast, get_args

from pydantic import BaseModel

from learning_commons_evaluators.contracts.loader import Contract, Preprocessing, Step
from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.inputs import (
    InputValue,
    primary_text_field,
    text_inputs,
    validate_inputs,
)
from learning_commons_evaluators.evaluators.source_passages import (
    render_source_passages,
    source_passage_fields,
)
from learning_commons_evaluators.features.image_source import ImageBounds, load_image
from learning_commons_evaluators.features.preprocessing import (
    check_implementation,
    format_number,
    run_preprocessing_step,
)
from learning_commons_evaluators.prompts.render import render_prompt
from learning_commons_evaluators.providers import (
    ImageAttachment,
    ImageMediaType,
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
from learning_commons_evaluators.telemetry.utils import utf16_length

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


def step_for(contract: Contract) -> Step:
    """The step the convention names: ``evaluate_{slug}``, where slug is the id's last segment."""
    return contract.step(f"evaluate_{contract.evaluator.slug}")


#: Read off the ``ImageMediaType`` literal, so a format added there is accepted here too.
_SUPPORTED_FORMATS: tuple[ImageMediaType, ...] = get_args(ImageMediaType)


def _is_number(value: object) -> TypeGuard[int | float]:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


@dataclass(frozen=True)
class AttachedInput:
    """An input whose files the step attaches, paired with the ``x-image`` bounds on its items."""

    input: str
    bounds: ImageBounds


def attachments_of(
    step: Step, input_schema: Mapping[str, Any], evaluator_name: str
) -> tuple[AttachedInput, ...]:
    """The step's attached inputs, each paired with the ``x-image`` bounds on its items.

    Read from the contract, and refused at class creation if a declaration cannot be
    honoured: an attached input without complete bounds, or of a kind this SDK cannot send,
    would otherwise reach the model unchecked or not at all. A missing or misspelled bound
    would compare against nothing and silently pass, so every field is checked here.
    """
    properties: Mapping[str, Any] = input_schema.get("properties", {})
    required = input_schema.get("required", [])
    attached: list[AttachedInput] = []
    for entry in step.attachments:

        def refuse(why: str, name: str = entry.input) -> NoReturn:
            raise ValueError(f'{evaluator_name} config.json attaches "{name}": {why}')

        if entry.kind != "image":
            refuse(f'kind "{entry.kind}" is not supported; this SDK sends only images.')
        spec = properties.get(entry.input)
        # Optional or non-array, a request could omit the images and be sent without them.
        if not isinstance(spec, Mapping) or spec.get("type") != "array":
            refuse("it must be an array input.")
        if entry.input not in required:
            refuse("it must be listed in `required`.")
        least, most = spec.get("minItems"), spec.get("maxItems")
        if not _is_number(least) or least < 1:
            refuse("it must declare `minItems` of at least 1.")
        if not _is_number(most) or most < least:
            refuse("it must declare `maxItems` of at least `minItems`.")
        items = spec.get("items")
        if not isinstance(items, Mapping) or items.get("type") != "string":
            refuse("its items must be strings (file paths).")
        declared = items.get("x-image")
        if not isinstance(declared, Mapping):
            refuse("its items need an `x-image` block.")
        formats = declared.get("formats")
        if (
            not isinstance(formats, list)
            or not formats
            or not all(f in _SUPPORTED_FORMATS for f in formats)
        ):
            refuse(
                "`x-image.formats` must be a non-empty list drawn from "
                f"{', '.join(_SUPPORTED_FORMATS)}."
            )
        if declared.get("detect") != "signature":
            refuse('`x-image.detect` must be "signature".')
        for key in ("min_bytes", "max_bytes", "min_edge", "max_edge"):
            if not _is_number(declared.get(key)):
                refuse(f"`x-image.{key}` must be a number.")
        bounds = ImageBounds(
            formats=tuple(formats),
            detect="signature",
            min_bytes=declared["min_bytes"],
            max_bytes=declared["max_bytes"],
            min_edge=declared["min_edge"],
            max_edge=declared["max_edge"],
        )
        if bounds.min_bytes > bounds.max_bytes:
            refuse("`x-image.min_bytes` exceeds `max_bytes`.")
        if bounds.min_edge > bounds.max_edge:
            refuse("`x-image.min_edge` exceeds `max_edge`.")
        attached.append(AttachedInput(entry.input, bounds))
    return tuple(attached)


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
    _attachments: ClassVar[tuple[AttachedInput, ...]]

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
        cls._attachments = attachments_of(step, contract.input_schema, name)
        # An attached input is an array of paths, never the primary text: that is the
        # first declared *string* input, so the attached ones are passed over by type.
        cls._text_field = primary_text_field(contract.input_schema)
        cls.metadata = EvaluatorMetadata.from_contract(contract, (step.model.provider,))

    def __init__(self, config: Any = None, /, **fields: Any) -> None:
        super().__init__(config, **fields)
        assert self._step.model is not None  # established at class creation
        self.provider: LLMProvider = self._create_configured_provider(
            self._vendor, self._step.model.name
        )
        # Refused here, not at call time: a provider that ignores attachments would otherwise
        # judge the claim with no image and return a confident verdict about nothing.
        if self._attachments and not getattr(self.provider, "supports_attachments", False):
            raise ConfigurationError(
                f"{self.metadata.label} attaches images to each request, and the configured "
                f'provider "{self.provider.label}" does not declare support for attachments.'
            )

    async def evaluate(
        self, input: InputT | None = None, /, **fields: Any
    ) -> EvaluationResult[OutputT]:
        """Evaluate the contract's inputs, passed as the typed input model or by name.

        :raises InputValidationError: an input is missing, unknown, or outside its schema;
            or an attached image cannot be read, is not an accepted format by its bytes, or
            falls outside the contract's ``x-image`` size or edge bounds.
        :raises ConfigurationError: the provider rejected the configured model id, or a
            required placeholder has no value from the source the contract names.
        :raises DependencyError: the provider call failed (``AuthenticationError``,
            ``RateLimitError``, ``NetworkError``, ``RequestTimeoutError``, ``LLMProviderError``).
        :raises LLMOutputProcessingError: the model's response failed its output schema
            after ``max_retries`` immediate resamples.
        """
        context = {"evaluator": self.metadata.id, "operation": "evaluate"}
        # Argument shape is a programmer error, raised as such; everything from validation
        # on is an evaluation failure, logged, classified, and telemetered.
        raw = self._raw_fields(input, fields)
        with self._telemetry_run(self.provider.label) as run:
            try:
                validated = validate_inputs(raw, self.contract.input_schema)
                # Attached inputs are files, never prompt text; only the other inputs render.
                values = text_inputs(validated, attached={a.input for a in self._attachments})
                text = values.get(self._text_field, "") if self._text_field else ""
                run.text_length = utf16_length(text)
                run.grade = values.get("grade_level", "")
                self.logger.info(
                    "Starting %s evaluation",
                    self.metadata.label,
                    extra={**context, "grade_level": run.grade, "text_length": run.text_length},
                )

                messages = self._render_messages(values, validated)
                attachments = await self._load_attachments(validated)
                # Passed only when there are some, so a text-only provider is never handed a
                # parameter it may not declare.
                extra: dict[str, Any] = {"attachments": attachments} if attachments else {}
                dependency, model = provider_context(self.provider)
                assert self._step.model is not None
                response = await call_with_resampling(
                    lambda: self.provider.generate_structured(
                        messages,
                        self.output_model,
                        temperature=self.effective_temperature(self._step.temperature),
                        **extra,
                    ),
                    max_retries=self.config.max_retries,
                    dependency=dependency,
                    model=model,
                    logger=self.logger,
                )
                run.step(self._step.id, self.provider.label, response.latency_ms, response.usage)

                elapsed_ms = run.elapsed_ms
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
                        "grade_level": run.grade,
                        "score": getattr(response.data, outcome.score, None) if outcome else None,
                        "processing_time_ms": elapsed_ms,
                    },
                )
                return cast(EvaluationResult[OutputT], result)
            except Exception as error:
                self.logger.error(
                    "%s evaluation failed",
                    self.metadata.label,
                    extra={
                        **context,
                        "grade_level": run.grade,
                        "error": type(error).__name__,
                        "processing_time_ms": run.elapsed_ms,
                    },
                )
                # Nothing is re-classified here. Every provider failure was already mapped by
                # ``call_with_resampling``; anything else reaching this point is a fault in this
                # SDK, and wrapping it as a provider error would name a service that did not
                # fail (spec §6.2) and hide the bug. The event is emitted as it leaves the
                # ``_telemetry_run`` block.
                raise

    # --- pieces of the flow ------------------------------------------------------------

    async def _load_attachments(
        self, values: Mapping[str, InputValue]
    ) -> tuple[ImageAttachment, ...]:
        """Every attached file, read in array order after validation and before any paid call.

        Read once per evaluation, not per resample. The reads are blocking file I/O, so they
        run off the event loop.
        """
        loaded: list[ImageAttachment] = []
        for attached in self._attachments:
            paths = values[attached.input]  # required, and validated as an array of strings
            for index, path in enumerate(paths):
                assert isinstance(path, str)  # attachments_of refuses any other item type
                loaded.append(
                    await asyncio.to_thread(
                        load_image, f"{attached.input}[{index}]", path, attached.bounds
                    )
                )
        return tuple(loaded)

    def _prompt_inputs(
        self, values: Mapping[str, str], validated: Mapping[str, InputValue] | None = None
    ) -> dict[str, str]:
        """Every placeholder the step declares, resolved from the source the contract names.

        ``validated`` keeps each array as its items. A length computation counts those
        items, and a ``SourcePassage`` field is rendered to markdown, both before a
        placeholder reads the field.
        """
        rendered = dict(values)
        if validated is not None:
            for field in source_passage_fields(self.contract.input_schema):
                passages = validated.get(field)
                if isinstance(passages, tuple):
                    rendered[field] = render_source_passages(passages)

        computed: dict[str, str] = {}
        for entry in self._preprocessing:
            if entry.condition is not None and not entry.condition.holds(dict(values)):
                continue
            assert entry.python is not None and entry.output is not None
            if entry.python.library == "builtins" and entry.python.function == "len":
                # Count the list, not the markdown it is about to become.
                counted = (
                    validated.get(entry.input) if validated is not None and entry.input else None
                )
                computed[entry.output] = format_number(
                    run_preprocessing_step(counted, entry.python)
                )
                continue
            source = values.get(entry.input or "", "")
            computed[entry.output] = format_number(run_preprocessing_step(source, entry.python))

        assert self._step.prompt is not None
        inputs: dict[str, str] = {}
        for name, placeholder in self._step.prompt.placeholders.items():
            kind, _, rest = placeholder.source.partition(".")
            if placeholder.source == "input":
                value = rendered.get(name)
            elif kind == "input":
                value = rendered.get(rest)
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

    def _render_messages(
        self, values: Mapping[str, str], validated: Mapping[str, InputValue] | None = None
    ) -> list[Message]:
        assert self._step.prompt is not None
        inputs = self._prompt_inputs(values, validated)
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


__all__ = ["AttachedInput", "SingleStepEvaluator", "attachments_of", "step_for"]
