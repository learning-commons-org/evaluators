"""The evaluator for a contract with more than one model call.

Steps run in the order the contract declares them, skipping any whose ``condition`` the
inputs do not satisfy. Each step's placeholders are resolved from the sources the contract
names — a caller input, a preprocessing output, or an earlier step's output — and any
preprocessing they need runs first. So the run order, the branch a grade takes, and the fact
that step two reads step one are all consequences of ``config.json`` rather than of the
order someone wrote the code in.

A concrete evaluator is a declaration::

    class SentenceStructureEvaluator(
        MultiStepEvaluator[SentenceStructureInput, SentenceStructureOutput]
    ):
        contract = load_contract("text_complexity.ela_reading.sentence_structure")
        input_model = SentenceStructureInput
        output_model = SentenceStructureOutput
        step_models = {
            "sentence_analysis": SentenceAnalysis,
            "classify_complexity": SentenceStructureOutput,
        }
        computations = {"compute_ground_truth_counts": compute_ground_truth_counts, ...}

``step_models`` names every declared step, so a contract that gains or renames one fails at
import rather than running a step whose output nothing validates; ``None`` declares a step
whose answer is prose, which reaches the next prompt as the text the model returned.
``computations`` supplies the functions a ``custom`` preprocessing entry names — ``custom``
means the contract names a computation instead of describing it, and keying on the declared
name is what keeps the two honest.

The single-step case has its own base rather than sharing this one: a lone step needs none
of the resolution below and reads better without it.
"""

from __future__ import annotations

import json
import math
from collections.abc import Callable, Mapping, Sequence
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
    TokenUsage,
    call_with_resampling,
    provider_context,
    provider_label,
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

#: A preprocessing entry the SDK supplies as a function rather than as a library call.
CUSTOM_KIND = "custom"
#: A preprocessing entry whose value is the text of a document the contract names.
DOCUMENT_KIND = "load_rubric_text"

#: Prefixes of ``prompt.placeholders[].source`` and of a preprocessing entry's ``input``.
_INPUT_PREFIX = "input."
_PREPROCESSING_PREFIX = "preprocessing."
_STEP_PREFIX = "steps."
_STEP_SUFFIX = ".output"


def step_id_of(source: str) -> str:
    """The step id in a ``steps.<id>.output`` reference."""
    return source[len(_STEP_PREFIX) :].removesuffix(_STEP_SUFFIX)


def _as_javascript_numbers(value: Any) -> Any:
    """``value`` with every number written the way JavaScript writes it.

    ``JSON.stringify`` emits an integral float as ``2`` where Python's ``json`` emits
    ``2.0``, and ``null`` for a non-finite one where Python emits invalid JSON (``NaN``).
    This is the rule :func:`~learning_commons_evaluators.features.preprocessing.format_number`
    applies to a scalar, applied through nested structures.
    """
    if isinstance(value, bool):
        return value  # before the numeric checks: bool is an int
    if isinstance(value, float):
        if not math.isfinite(value):
            return None
        return int(value) if value.is_integer() else value
    if isinstance(value, Mapping):
        return {key: _as_javascript_numbers(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_as_javascript_numbers(item) for item in value]
    return value


def as_prompt_text(value: object) -> str:
    """A step's output as the next prompt reads it: its own text, or compact JSON.

    Rendered as the TypeScript SDK's ``JSON.stringify`` renders it, so a structured step
    output binds the same bytes in both SDKs: compact separators, the characters themselves
    rather than ``\\uXXXX`` escapes, and JavaScript's number tokens.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json")
    return json.dumps(_as_javascript_numbers(value), separators=(",", ":"), ensure_ascii=False)


class MultiStepEvaluator(BaseEvaluator, Generic[InputT, OutputT]):
    """Base for every evaluator whose contract declares more than one LLM step."""

    #: The declarations a concrete class makes, alongside ``contract`` from the base.
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]
    #: Output model for each declared step id; ``None`` for a step that answers in prose.
    step_models: ClassVar[Mapping[str, type[BaseModel] | None]] = {}
    #: ``custom`` preprocessing, keyed by ``implementation.python.function``.
    computations: ClassVar[Mapping[str, Callable[[Any], str]]] = {}

    # Resolved from the contract at class creation.
    _steps: ClassVar[tuple[Step, ...]]
    _preprocessing: ClassVar[tuple[Preprocessing, ...]]
    _text_field: ClassVar[str | None]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, "contract"):
            return  # an abstract intermediate; the declaring subclass resolves
        contract = cls.contract
        _check_steps(cls, contract)
        _check_preprocessing(cls, contract)

        cls._steps = tuple(contract.steps)
        cls._preprocessing = tuple(contract.preprocessing)
        cls._text_field = primary_text_field(contract.input_schema)
        cls.metadata = EvaluatorMetadata.from_contract(contract, contract.providers)

    def __init__(self, config: Any = None, /, **fields: Any) -> None:
        super().__init__(config, **fields)
        # One client per distinct provider and model, not per step: two steps on the same
        # model share a client, so a two-step evaluator on one model opens one connection.
        # Keyed on the model that will actually be called, so a ``model_override`` — which
        # sends every step to one model — collapses to one client rather than keeping the
        # default models' distinctions and building an identical client per step.
        by_model: dict[str, LLMProvider] = {}
        self._providers: dict[str, LLMProvider] = {}
        for step in self._steps:
            assert step.model is not None  # established at class creation
            key = provider_label(*self.effective_model(step.model.provider, step.model.name))
            provider = by_model.get(key)
            if provider is None:
                provider = self._create_configured_provider(step.model.provider, step.model.name)
                by_model[key] = provider
            self._providers[step.id] = provider

    async def evaluate(
        self, input: InputT | None = None, /, **fields: Any
    ) -> EvaluationResult[OutputT]:
        """Evaluate the contract's inputs, passed as the typed input model or by name.

        :raises InputValidationError: an input is missing, unknown, or outside its schema.
        :raises ConfigurationError: a provider rejected the configured model id, or the
            contract is inconsistent for these inputs — no branch runs, a placeholder has
            no value, or no single preprocessing entry produces one it needs. Registry data
            is the caller's domain, not a service's (spec §6.1).
        :raises DependencyError: a provider call failed (``AuthenticationError``,
            ``RateLimitError``, ``NetworkError``, ``RequestTimeoutError``, ``LLMProviderError``).
        :raises LLMOutputProcessingError: a step's response failed its output schema after
            ``max_retries`` immediate resamples.
        """
        context = {"evaluator": self.metadata.id, "operation": "evaluate"}
        raw = self._raw_fields(input, fields)
        # Until a step starts, the model named is the one the first declared step would
        # call, so a failure before any of them — a rejected input — still reports a model.
        with self._telemetry_run(self._providers[self._steps[0].id].label) as run:
            try:
                values = validate_inputs(raw, self.contract.input_schema)
                text = values.get(self._text_field, "") if self._text_field else ""
                run.text_length = utf16_length(text)
                run.grade = values.get("grade_level", "")
                self.logger.info(
                    "Starting %s evaluation",
                    self.metadata.label,
                    extra={**context, "grade_level": run.grade, "text_length": run.text_length},
                )

                plan = self._plan(values)
                outputs: dict[str, Any] = {}
                computed: dict[str, str] = {}

                for step in plan:
                    provider = self._providers[step.id]
                    # Named before the call rather than after it, so a step that fails is
                    # reported against its own model and not against the last one to finish.
                    run.provider = provider.label
                    self.logger.debug(
                        "Running step %s", step.id, extra={**context, "operation": step.id}
                    )
                    output, step_usage, latency_ms = await self._run_step(
                        step, provider, self._render_messages(step, values, outputs, computed)
                    )
                    outputs[step.id] = output
                    run.step(step.id, provider.label, latency_ms, step_usage)

                final = outputs[plan[-1].id]
                if not isinstance(final, self.output_model):
                    raise ConfigurationError(
                        f'The last step {self.metadata.name} ran, "{plan[-1].id}", produces '
                        f"{type(final).__name__} rather than {self.output_model.__name__}; a branch "
                        "of its contract ends on a step whose output is not the evaluator's result."
                    )

                elapsed_ms = run.elapsed_ms
                # Every planned step ran to get here, and a plan is never empty.
                usage = run.token_usage
                assert usage is not None
                result: EvaluationResult[Any] = EvaluationResult(
                    evaluator=self.metadata.id,
                    result=final,
                    metadata=EvaluationMetadata(
                        # Every model that ran, in run order. One step, or several sharing a
                        # model, report that model alone; a branch that spans two report both,
                        # because naming just the last would hide the model that fed it.
                        model="+".join(dict.fromkeys(stage.provider for stage in run.stages)),
                        processing_time_ms=elapsed_ms,
                        token_usage=EvaluationTokenUsage(
                            input_tokens=usage.input_tokens, output_tokens=usage.output_tokens
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
                        "score": getattr(final, outcome.score, None) if outcome else None,
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
                        "completed_steps": len(run.stages),
                    },
                )
                # Nothing is re-classified here. Every provider failure was already mapped by
                # ``call_with_resampling``, which knows which step's client raised it; anything
                # else reaching this point is a fault in this SDK, and wrapping it as a provider
                # error would name a service that did not fail (spec §6.2) and hide the bug. The
                # event is emitted as it leaves the ``_telemetry_run`` block.
                raise

    # --- the run ------------------------------------------------------------------------

    def _plan(self, values: Mapping[str, str]) -> list[Step]:
        """The steps these inputs run, in declared order.

        A step with no condition always runs; a conditional one runs only for the inputs it
        names, which is how a contract expresses "grades 3-4 take this branch".
        """
        plan = [
            step for step in self._steps if step.condition is None or step.condition.holds(values)
        ]
        if not plan:
            raise ConfigurationError(
                f"No step of {self.metadata.name} runs for these inputs; every step it "
                "declares is conditional and none of the conditions hold."
            )
        return plan

    async def _run_step(
        self, step: Step, provider: LLMProvider, messages: Sequence[Message]
    ) -> tuple[Any, TokenUsage, int]:
        """One step's model call, resampled on an output the schema rejects (§6.3).

        Reports what the answer cost and how long the call that produced it took, which is
        the per-step breakdown telemetry carries.
        """
        dependency, model = provider_context(provider)
        schema = self.step_models[step.id]
        temperature = self.effective_temperature(step.temperature)
        if schema is None:
            prose = await call_with_resampling(
                lambda: provider.generate_text(messages, temperature=temperature),
                max_retries=self.config.max_retries,
                dependency=dependency,
                model=model,
                logger=self.logger,
            )
            # Trimmed: the answer is pasted into the next prompt, where the model's
            # surrounding blank lines would read as structure it did not intend.
            return prose.text.strip(), prose.usage, prose.latency_ms
        structured = await call_with_resampling(
            lambda: provider.generate_structured(messages, schema, temperature=temperature),
            max_retries=self.config.max_retries,
            dependency=dependency,
            model=model,
            logger=self.logger,
        )
        return structured.data, structured.usage, structured.latency_ms

    # --- resolving one step's prompt -----------------------------------------------------

    def _render_messages(
        self,
        step: Step,
        values: Mapping[str, str],
        outputs: Mapping[str, Any],
        computed: dict[str, str],
    ) -> list[Message]:
        assert step.prompt is not None  # established at class creation
        inputs = self._prompt_inputs(step, values, outputs, computed)
        placeholders = list(step.prompt.placeholders)
        return [
            Message(
                role=message.role,
                content=render_prompt(
                    self.contract.document(message.source_path), inputs, placeholders
                ),
            )
            for message in step.prompt.messages
        ]

    def _prompt_inputs(
        self,
        step: Step,
        values: Mapping[str, str],
        outputs: Mapping[str, Any],
        computed: dict[str, str],
    ) -> dict[str, str]:
        """Every placeholder the step declares, resolved from the source the contract names."""
        assert step.prompt is not None
        inputs: dict[str, str] = {}
        for name, placeholder in step.prompt.placeholders.items():
            value = self._resolve(name, placeholder.source, values, outputs, computed)
            if value is None:
                if placeholder.required:
                    raise ConfigurationError(
                        f'Placeholder "{name}" in {self.metadata.name} has no value '
                        f"from source {placeholder.source!r}."
                    )
                continue
            inputs[name] = value
        return inputs

    def _resolve(
        self,
        name: str,
        source: str,
        values: Mapping[str, str],
        outputs: Mapping[str, Any],
        computed: dict[str, str],
    ) -> str | None:
        """One placeholder, from whichever of the four sources the contract names."""
        if source == "input":
            return values.get(name)
        if source.startswith(_INPUT_PREFIX):
            return values.get(source[len(_INPUT_PREFIX) :])
        if source.startswith(_PREPROCESSING_PREFIX):
            return self._preprocess(source[len(_PREPROCESSING_PREFIX) :], values, outputs, computed)
        step_id = step_id_of(source)
        if step_id not in outputs:
            raise ConfigurationError(
                f'Placeholder "{name}" reads step "{step_id}", which has not run. Steps run '
                f"in the order {self.metadata.name} declares them."
            )
        return as_prompt_text(outputs[step_id])

    def _preprocess(
        self,
        output: str,
        values: Mapping[str, str],
        outputs: Mapping[str, Any],
        computed: dict[str, str],
    ) -> str:
        """One preprocessing output, computed once per evaluation.

        Selected by output name rather than by entry id: several entries may declare the
        same output under mutually exclusive conditions, which is how a contract expresses
        "use the rubric for this grade".
        """
        cached = computed.get(output)
        if cached is not None:
            return cached

        applicable = [
            entry
            for entry in self._preprocessing
            if entry.output == output and (entry.condition is None or entry.condition.holds(values))
        ]
        # Both are contract faults, and both would otherwise reach the model as an empty or
        # an arbitrary placeholder rather than as an error.
        if not applicable:
            raise ConfigurationError(
                f'No preprocessing entry of {self.metadata.name} produces "{output}" for '
                "these inputs."
            )
        if len(applicable) > 1:
            named = ", ".join(entry.id for entry in applicable)
            raise ConfigurationError(
                f"{len(applicable)} preprocessing entries of {self.metadata.name} produce "
                f'"{output}" for these inputs: {named}. Their conditions should be mutually '
                "exclusive."
            )

        value = self._run_entry(applicable[0], values, outputs)
        computed[output] = value
        return value

    def _run_entry(
        self, entry: Preprocessing, values: Mapping[str, str], outputs: Mapping[str, Any]
    ) -> str:
        """One preprocessing entry: a named document, a supplied function, or a library call."""
        if entry.kind == DOCUMENT_KIND:
            assert entry.source_path is not None  # established at class creation
            return self.contract.document(entry.source_path)

        # An entry's own input may be a step output, which is what orders the run. Checked
        # for every kind: a library computation would otherwise run on the empty string and
        # hide a forward reference, or a typo in the step id, behind a plausible number.
        source = entry.input or ""
        if source.startswith(_STEP_PREFIX):
            step_id = step_id_of(source)
            if step_id not in outputs:
                raise ConfigurationError(
                    f'Preprocessing "{entry.id}" of {self.metadata.name} reads "{source}", '
                    "which has not run yet."
                )
            resolved: Any = outputs[step_id]
        else:
            resolved = values.get(source, "")

        assert entry.python is not None  # established at class creation
        if entry.kind == CUSTOM_KIND:
            return self.computations[entry.python.function](resolved)
        return format_number(run_preprocessing_step(str(resolved), entry.python))


def _check_steps(cls: type[MultiStepEvaluator[Any, Any]], contract: Contract) -> None:
    """Fail unless the declaration accounts for every step the contract declares."""
    name = contract.evaluator.name
    if len(contract.steps) < 2:
        raise ValueError(
            f"{name} config.json declares {len(contract.steps)} step(s); MultiStepEvaluator "
            "runs more than one. Use the single-step base."
        )

    # A step id is the key the run stores a provider and an output under, so two steps
    # sharing one would alias: the second's output would overwrite the first's, and the
    # step_models check below would pass on a single entry covering both. Nothing else
    # catches it — the registry schema does not require step ids to be unique.
    declared: set[str] = set()
    for step in contract.steps:
        if step.id in declared:
            raise ValueError(
                f'Step "{step.id}" is declared twice in {name} config.json; a step id names '
                "one step, and the run keys its provider and its output on that id."
            )
        declared.add(step.id)

    for step in contract.steps:
        if step.type != "llm" or step.prompt is None or step.model is None:
            raise ValueError(f'Step "{step.id}" in {name} config.json is not an LLM step.')
        if step.optional:
            # There is no way for a caller to opt in, so running it would over-run the
            # contract and skipping it would under-run one the metadata described.
            raise ValueError(
                f'Step "{step.id}" in {name} config.json is optional, which no evaluator '
                "supports yet."
            )
        if step.id not in cls.step_models:
            raise ValueError(
                f'Step "{step.id}" in {name} config.json has no step_models entry. Name '
                "every step, with None for a step that answers in prose."
            )
        for placeholder, spec in step.prompt.placeholders.items():
            _check_placeholder_source(placeholder, spec.source, name, declared)

    for step_id in cls.step_models:
        if step_id not in declared:
            raise ValueError(
                f'step_models names "{step_id}", which {name} config.json does not declare.'
            )
    # Which steps can end a run, and so have to produce the evaluator's result. Not simply
    # the last declared one: when the trailing steps are conditional, whichever of them the
    # inputs select is the terminal step, and there may be several. Nor every step from the
    # last unconditional one onward, which would reject Vocabulary Complexity — its last
    # unconditional step is background_knowledge, whose prose feeds the next prompt and is
    # not the result. So: every step after the last unconditional one, and that step itself
    # only when nothing follows it.
    last_unconditional = max(
        (i for i, step in enumerate(contract.steps) if step.condition is None), default=-1
    )
    terminal = list(range(last_unconditional + 1, len(contract.steps))) or [last_unconditional]
    for index in terminal:
        step = contract.steps[index]
        if cls.step_models[step.id] is not cls.output_model:
            raise ValueError(
                f'Step "{step.id}" of {name} config.json can end a run, so it must produce '
                f"{cls.output_model.__name__}, which is what evaluate() returns."
            )
    # A trailing group of conditional steps that does not cover the input schema's enum
    # still lets a run end on the last unconditional step, which this rule exempts; that
    # case is caught during the evaluation instead.


def _check_placeholder_source(placeholder: str, source: str, name: str, declared: set[str]) -> None:
    if source == "input" or source.startswith((_INPUT_PREFIX, _PREPROCESSING_PREFIX)):
        return
    if not source.startswith(_STEP_PREFIX) or not source.endswith(_STEP_SUFFIX):
        raise ValueError(
            f'Placeholder "{placeholder}" in {name} config.json declares an unsupported '
            f'source "{source}".'
        )
    step_id = step_id_of(source)
    if step_id not in declared:
        raise ValueError(
            f'Placeholder "{placeholder}" in {name} config.json reads step "{step_id}", '
            "which it does not declare."
        )


def _check_entry_input(
    entry: Preprocessing, name: str, steps: set[str], inputs: Mapping[str, Any]
) -> None:
    """Fail unless a computation entry reads something the contract actually has.

    An entry's input is resolved from the validated caller inputs at evaluation, where an
    undeclared name reads as the empty string: the computation then succeeds on it and
    binds a plausible number, so a typo in the contract would reach the model as data
    rather than as an error.
    """
    source = entry.input or ""
    if not source:
        raise ValueError(
            f'Preprocessing "{entry.id}" in {name} config.json names no input to compute from.'
        )
    if source.startswith(_STEP_PREFIX):
        step_id = step_id_of(source)
        if step_id not in steps:
            raise ValueError(
                f'Preprocessing "{entry.id}" in {name} config.json reads step "{step_id}", '
                "which it does not declare."
            )
        return
    if source not in inputs:
        raise ValueError(
            f'Preprocessing "{entry.id}" in {name} config.json reads input "{source}", which '
            "its input_schema does not declare."
        )


def _check_preprocessing(cls: type[MultiStepEvaluator[Any, Any]], contract: Contract) -> None:
    """Fail unless this evaluator supplies what every preprocessing entry needs."""
    name = contract.evaluator.name
    steps = {step.id for step in contract.steps}
    inputs: Mapping[str, Any] = contract.input_schema.get("properties", {})
    for entry in contract.preprocessing:
        # As the single-step base does: an ``api`` entry has an endpoint, auth and
        # pagination to honour, and running it as a local computation would quietly do
        # something else. Three of them are declared in evals/ today, on math standards.
        if entry.type != "computation":
            raise ValueError(
                f'Preprocessing "{entry.id}" in {name} config.json is an "{entry.type}" entry; '
                "this base runs computations only."
            )
        if not entry.output:
            raise ValueError(
                f'Preprocessing "{entry.id}" in {name} config.json names no output, so no '
                "placeholder can read it."
            )
        if entry.kind == DOCUMENT_KIND:
            if not entry.source_path:
                raise ValueError(
                    f'Preprocessing "{entry.id}" in {name} config.json names no source_path '
                    "to load."
                )
            contract.document(entry.source_path)  # raises, naming the file, if unbundled
            continue
        _check_entry_input(entry, name, steps, inputs)
        if entry.python is None:
            raise ValueError(
                f'Preprocessing "{entry.id}" in {name} config.json declares no Python '
                "implementation this evaluator can run."
            )
        if entry.kind == CUSTOM_KIND:
            if entry.python.function not in cls.computations:
                raise ValueError(
                    f'Preprocessing "{entry.id}" in {name} config.json declares custom '
                    f'function "{entry.python.function}", which this evaluator does not '
                    "supply."
                )
            continue
        # A library or transform this SDK lacks is our gap, not the provider's: fail here,
        # at import, rather than inside the evaluation's error boundary.
        try:
            check_implementation(entry.python)
        except NotImplementedError as gap:
            raise NotImplementedError(
                f'Preprocessing "{entry.id}" in {name} config.json: {gap}'
            ) from None


__all__ = [
    "CUSTOM_KIND",
    "DOCUMENT_KIND",
    "MultiStepEvaluator",
    "as_prompt_text",
    "step_id_of",
]
