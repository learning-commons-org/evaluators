"""Math Standards Alignment: does an assessment question assess a standard's components?

One model call judges the question against every learning component the Knowledge Graph
holds for one standard, and the payload reports a verdict per component alongside the
aligned and total counts. There is no single score: the contract declares no ``outcome``
block, so :func:`~learning_commons_evaluators.read_outcome` reports ``None`` for this
evaluator, as it does in the TypeScript SDK.

The standard is named by its CASE Network UUID. The registry contract also declares
``statement_code`` + ``jurisdiction``, which is what the TypeScript SDK accepts, and
resolving those through Knowledge Graph search is deliberately not in this release
(DSCR-2252) -- so this evaluator validates its own inputs rather than the contract's. A
code is only ever a lookup key for a UUID: the Knowledge Graph carries one copy of a
standard per adopting jurisdiction, each with its own UUID and often its own spelling of
the code, so the UUID is the identity and the search that resolves one is the deferred
part.

This is the only evaluator that calls a non-LLM dependency, so it is the only one holding
something to release. Close it when you are done -- ``async with``, :meth:`aclose`, or
:meth:`~learning_commons_evaluators.evaluators.base.BaseEvaluator.close` from sync code.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from learning_commons_evaluators.config import EvaluatorConfig
from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.contracts.loader import ModelSpec, Prompt, Step
from learning_commons_evaluators.dependencies.knowledge_graph import (
    AcademicStandard,
    KnowledgeGraphClient,
    LearningComponent,
)
from learning_commons_evaluators.errors import InputValidationError, LLMOutputProcessingError
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.evaluators.inputs import validate_inputs
from learning_commons_evaluators.evaluators.single_step import step_for
from learning_commons_evaluators.prompts.render import render_prompt
from learning_commons_evaluators.providers import (
    LLMProvider,
    Message,
    TokenUsage,
    call_with_resampling,
    provider_context,
)
from learning_commons_evaluators.schemas.academic_standards_alignment.mathematics.math_standards_alignment import (
    EVALUATOR_ID,
)
from learning_commons_evaluators.schemas.evaluator import (
    EvaluationMetadata,
    EvaluationResult,
    EvaluationTokenUsage,
)
from learning_commons_evaluators.schemas.kg_taxonomy import AcademicSubject
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata
from learning_commons_evaluators.telemetry.run import TelemetryRun
from learning_commons_evaluators.telemetry.utils import utf16_length

CONTRACT = load_contract(EVALUATOR_ID)
STEP = step_for(CONTRACT)


def _llm_step(step: Step) -> tuple[ModelSpec, Prompt]:
    """The model and prompt an LLM step carries, or a failure at import rather than later.

    A contract this evaluator cannot run is a packaging fault, not an evaluation failure,
    so it surfaces when the module is imported -- the same point the single-step factory
    rejects one.
    """
    if step.model is None or step.prompt is None:  # pragma: no cover - the contract has both
        raise ValueError(
            f'Step "{step.id}" in {CONTRACT.evaluator.name} config.json is not an LLM step.'
        )
    return step.model, step.prompt


_MODEL, _PROMPT = _llm_step(STEP)

#: The only subject this evaluator can judge. Its prompt is a mathematics rubric and its
#: contract declares mathematics standards, so a standard from another subject is refused
#: rather than scored against it.
ACADEMIC_SUBJECT = AcademicSubject.MATHEMATICS

#: What this release accepts. ``question`` is the contract's own property, so its bounds
#: and its failure message come from the registry rather than from a copy here;
#: ``case_identifier_uuid`` is this SDK's, because the contract does not declare it.
INPUT_SCHEMA: dict[str, Any] = {
    "properties": {
        "question": CONTRACT.input_schema["properties"]["question"],
        "case_identifier_uuid": {
            "type": "string",
            "description": (
                "CASE Network UUID of the math standard to evaluate against -- the "
                "Knowledge Graph's caseIdentifierUUID. Resolve one from a statement code "
                "with KnowledgeGraphClient.search_standards()."
            ),
            "minLength": 1,
        },
    },
    "required": ["question", "case_identifier_uuid"],
}

#: Contract inputs this release does not take. Named explicitly because the registry still
#: declares them and the TypeScript SDK still accepts them, so a caller reading the
#: contract, or porting across, reasonably tries them here and deserves better than being
#: told the key is unknown.
DEFERRED_INPUTS = ("statement_code", "jurisdiction")


# --- The model's answer ---------------------------------------------------------------


class LCEvaluation(BaseModel):
    """One learning component's verdict, as the model returns it.

    ``lc_id`` echoes back the Knowledge Graph identifier the prompt listed in brackets, so
    a verdict can be matched to the component it was meant for rather than to a position
    in a list.
    """

    model_config = ConfigDict(extra="forbid")

    lc_id: str
    reasoning: str
    answer: Literal["Yes", "No"]
    feedback: str


class BatchedLCEvaluation(BaseModel):
    """The step's structured output: one entry per learning component sent."""

    model_config = ConfigDict(extra="forbid")

    evaluations: list[LCEvaluation]


# --- The payload ------------------------------------------------------------------------


class LearningComponentResult(BaseModel):
    """One learning component and whether the question assesses it."""

    model_config = ConfigDict(extra="forbid")

    #: The Knowledge Graph identifier, so a verdict can be joined back to the component.
    identifier: str
    description: str
    reasoning: str
    aligned: bool
    feedback: str


class MathStandardsAlignmentResult(BaseModel):
    """What ``evaluate()`` resolves its ``result`` to.

    ``aligned_count`` of 0 with a ``total_count`` above it is a judgement; both at 0 means
    the standard has no components to judge, and nothing was measured.
    """

    model_config = ConfigDict(extra="forbid")

    statement_code: str = Field(
        description="The Knowledge Graph's code for the standard that was evaluated, "
        "empty when it carries none."
    )
    learning_components: list[LearningComponentResult]
    aligned_count: int = Field(ge=0)
    total_count: int = Field(ge=0)


class MathStandardsAlignmentEvaluator(BaseEvaluator):
    """Aligns one assessment question to one math standard's learning components.

    ::

        async with MathStandardsAlignmentEvaluator(
            anthropic_api_key="...", learning_commons_api_key="..."
        ) as evaluator:
            evaluation = await evaluator.evaluate(
                question="A playground is shaped like an L ...",
                case_identifier_uuid="6ba25656-d7cc-11e8-824f-0242ac160002",
            )

    :raises ConfigurationError: at construction, when ``anthropic_api_key`` or
        ``learning_commons_api_key`` is missing, so a missing key surfaces before any call.
    """

    contract = CONTRACT
    metadata = EvaluatorMetadata.from_contract(CONTRACT, (_MODEL.provider,))

    def __init__(
        self,
        config: EvaluatorConfig | None = None,
        /,
        *,
        knowledge_graph: KnowledgeGraphClient | None = None,
        **fields: Any,
    ) -> None:
        """Build the evaluator, its Anthropic provider, and its Knowledge Graph client.

        :param knowledge_graph: A client to use instead of one built from the config. It
            carries its own credentials, so ``learning_commons_api_key`` is not required
            alongside it, and closing it stays the caller's job.
        """
        # Assigned before super().__init__, which validates credentials and asks the hook
        # below whether an injected dependency already satisfies one.
        self._injected_knowledge_graph = knowledge_graph
        super().__init__(config, **fields)
        # The provider first: it builds its client per call, so a failure here leaves
        # nothing open, while the Knowledge Graph client opens a connection pool now.
        self.provider: LLMProvider = self._create_configured_provider(_MODEL.provider, _MODEL.name)
        self._knowledge_graph = knowledge_graph or KnowledgeGraphClient.from_config(self.config)

    def _credentials_satisfied_by_injection(self) -> frozenset[str]:
        if self._injected_knowledge_graph is None:
            return frozenset()
        return frozenset({"learning_commons_api_key"})

    async def evaluate(
        self, input: Any = None, /, **fields: Any
    ) -> EvaluationResult[MathStandardsAlignmentResult]:
        """Judge ``question`` against the learning components of one standard.

        :param question: The assessment item students see.
        :param case_identifier_uuid: CASE Network UUID of the standard.

        :raises InputValidationError: an input is missing, unknown, or outside its schema;
            the UUID is malformed, names no standard, or names one from another subject.
        :raises DependencyError: the Knowledge Graph or the provider call failed
            (``KnowledgeGraphError``, ``AuthenticationError``, ``RateLimitError``,
            ``NetworkError``, ``RequestTimeoutError``, ``LLMProviderError``).
        :raises LLMOutputProcessingError: the model's response failed its schema after
            ``max_retries`` resamples, or judged fewer components than it was sent.
        """
        context = {"evaluator": self.metadata.id, "operation": "evaluate"}
        raw = self._raw_fields(input, fields)
        with self._telemetry_run(self.provider.label) as run:
            try:
                values = self._validated(raw)
                question, uuid = values["question"], values["case_identifier_uuid"]
                run.text_length = utf16_length(question)
                self.logger.info(
                    "Starting %s evaluation",
                    self.metadata.label,
                    extra={**context, "standard": uuid, "text_length": run.text_length},
                )

                statement_code = await self._statement_code(uuid, context)
                component_set = await self._knowledge_graph.get_learning_component_set(uuid)
                components = component_set.components
                if component_set.undescribed_count:
                    # total_count reports what was judged, so say why it is short of what
                    # the standard holds rather than letting the gap look like a miscount.
                    self.logger.warning(
                        "Standard has %d learning component(s) with no description; "
                        "they cannot be judged and are not counted",
                        component_set.undescribed_count,
                        extra={**context, "standard": uuid, "statement_code": statement_code},
                    )

                if not components:
                    # Nothing to judge, so nothing to ask: a standard with no authored
                    # components resolves without a model call, and the zero token usage
                    # in the envelope is what says so.
                    self.logger.info(
                        "Standard has no evaluable learning components; no model call made",
                        extra={**context, "standard": uuid, "statement_code": statement_code},
                    )
                    return self._envelope(
                        MathStandardsAlignmentResult(
                            statement_code=statement_code,
                            learning_components=[],
                            aligned_count=0,
                            total_count=0,
                        ),
                        run,
                    )

                dependency, model = provider_context(self.provider)
                response = await call_with_resampling(
                    lambda: self.provider.generate_structured(
                        self._render_messages(question, components),
                        BatchedLCEvaluation,
                        temperature=self.effective_temperature(STEP.temperature),
                    ),
                    max_retries=self.config.max_retries,
                    dependency=dependency,
                    model=model,
                    logger=self.logger,
                )
                run.step(STEP.id, self.provider.label, response.latency_ms, response.usage)

                judged = self._verified(components, response.data, statement_code)
                result = MathStandardsAlignmentResult(
                    statement_code=statement_code,
                    learning_components=judged,
                    aligned_count=sum(1 for component in judged if component.aligned),
                    total_count=len(components),
                )
                self.logger.info(
                    "%s evaluation completed successfully",
                    self.metadata.label,
                    extra={
                        **context,
                        "standard": uuid,
                        "statement_code": statement_code,
                        "aligned_count": result.aligned_count,
                        "total_count": result.total_count,
                        "processing_time_ms": run.elapsed_ms,
                    },
                )
                return self._envelope(result, run, response.usage)
            except Exception as error:
                self.logger.error(
                    "%s evaluation failed",
                    self.metadata.label,
                    extra={
                        **context,
                        "error": type(error).__name__,
                        "processing_time_ms": run.elapsed_ms,
                    },
                )
                # Nothing is re-classified here: the Knowledge Graph client maps its own
                # failures and ``call_with_resampling`` maps the provider's, so anything
                # else reaching this point is a fault in this SDK and wrapping it would
                # name a service that did not fail (spec §6.2).
                raise

    # --- pieces of the flow ------------------------------------------------------------

    @staticmethod
    def _validated(raw: Any) -> dict[str, str]:
        """The caller's inputs, checked against what this release accepts.

        The UUID's shape is checked here rather than left to the Knowledge Graph client,
        so a typo costs no request, reads as the caller's input rather than the service's,
        and is rejected the same way whichever client this evaluator was given.
        """
        if isinstance(raw, Mapping):
            deferred = [name for name in DEFERRED_INPUTS if name in raw]
            if deferred:
                raise InputValidationError(
                    f"{', '.join(deferred)} {'are' if len(deferred) > 1 else 'is'} not "
                    "accepted in this release. Pass case_identifier_uuid, the standard's "
                    "CASE Network UUID; resolve one from a statement code with "
                    "KnowledgeGraphClient.search_standards()."
                )
        values = validate_inputs(raw, INPUT_SCHEMA)
        try:
            UUID(values["case_identifier_uuid"])
        except ValueError as error:
            raise InputValidationError(
                "case_identifier_uuid must be a CASE Network UUID, got "
                f"{values['case_identifier_uuid']!r}."
            ) from error
        return values

    async def _statement_code(self, uuid: str, context: Mapping[str, Any]) -> str:
        """The Knowledge Graph's own spelling of the standard's code, once it is a math one.

        Read rather than taken from the input, because the input is a UUID: the payload
        reports the code so a result can be joined to a report keyed on codes, which is
        what the TypeScript SDK's payload carries. Every field but the UUID is optional in
        the Knowledge Graph, so a sparsely authored standard yields an empty code; that is
        said out loud rather than passed off as a code.

        This is also where the subject is checked, because it is the one place the standard
        itself is read. It runs before the learning components are fetched and before any
        model call, so a standard this evaluator cannot judge costs one request rather than
        a full evaluation.

        :raises InputValidationError: when the standard belongs to another subject.
        """
        standard = await self._knowledge_graph.get_academic_standard(uuid)
        self._require_subject(standard, context)
        if standard.statement_code:
            return standard.statement_code
        self.logger.warning(
            "Standard carries no statement code; the payload reports an empty one",
            extra={**context, "standard": uuid},
        )
        return ""

    def _require_subject(self, standard: AcademicStandard, context: Mapping[str, Any]) -> None:
        """Refuse a standard from another subject before it reaches the math rubric.

        A UUID names any standard in the Knowledge Graph, including an ELA one, and nothing
        downstream would notice: the components would be fetched and judged against a
        mathematics prompt, and the result would read as a finding rather than a mistake.

        An unknown subject is allowed through. ``None`` here means either that the service
        stated no subject or that it stated one this SDK's taxonomy does not yet carry, and
        the client maps both to ``None`` on purpose (see ``_taxonomy``) -- so refusing on it
        would turn our own staleness into a rejected call. It is logged instead.
        """
        subject = standard.academic_subject
        if subject is None:
            self.logger.debug(
                "Standard states no subject this SDK recognizes; evaluating it anyway",
                extra={**context, "standard": standard.case_identifier_uuid},
            )
            return
        if subject is not ACADEMIC_SUBJECT:
            raise InputValidationError(
                f"Standard {standard.case_identifier_uuid} is a {subject.value} standard; "
                f"{self.metadata.name} judges {ACADEMIC_SUBJECT.value} standards. Pass the "
                "UUID of a mathematics standard."
            )

    def _render_messages(
        self, question: str, components: Sequence[LearningComponent]
    ) -> list[Message]:
        """The step's prompts, with the components numbered as both SDKs number them.

        Each identifier is carried in brackets so the model can echo it back, which is what
        lets :meth:`_verified` check that every component sent was judged.
        """
        inputs = {
            "question": question,
            "learning_components": "\n".join(
                f"{position}. [{component.identifier}] {component.description}"
                for position, component in enumerate(components, start=1)
            ),
        }
        placeholders = list(_PROMPT.placeholders)
        return [
            Message(
                role=message.role,
                content=render_prompt(CONTRACT.document(message.source_path), inputs, placeholders),
            )
            for message in _PROMPT.messages
        ]

    @staticmethod
    def _verified(
        components: Sequence[LearningComponent],
        answer: BatchedLCEvaluation,
        statement_code: str,
    ) -> list[LearningComponentResult]:
        """One result per component sent, matched on the identifier the model echoed back.

        Verdicts for identifiers that were never sent are dropped, and a component sent but
        not judged fails the evaluation rather than being reported: nothing was measured
        for it, and ``aligned: false`` would read as a judgement that it does not align.
        """
        sent = {component.identifier for component in components}
        judged = {entry.lc_id: entry for entry in answer.evaluations if entry.lc_id in sent}
        missing = [c.identifier for c in components if c.identifier not in judged]
        if missing:
            raise LLMOutputProcessingError(
                "LLM response missing verified evaluations for LC identifiers: "
                f"{', '.join(missing)}. Standard: {statement_code}",
                [{"path": "evaluations", "identifier": identifier} for identifier in missing],
            )
        return [
            LearningComponentResult(
                identifier=component.identifier,
                description=component.description,
                reasoning=judged[component.identifier].reasoning,
                aligned=judged[component.identifier].answer == "Yes",
                feedback=judged[component.identifier].feedback,
            )
            for component in components
        ]

    def _envelope(
        self,
        result: MathStandardsAlignmentResult,
        run: TelemetryRun,
        usage: TokenUsage | None = None,
    ) -> EvaluationResult[MathStandardsAlignmentResult]:
        """Wrap a payload in the shared envelope (spec §5.1).

        ``model`` is the configured model even when no call was made -- a standard with no
        learning components resolves without one -- and the zero token usage is what says
        so.
        """
        return EvaluationResult(
            evaluator=self.metadata.id,
            result=result,
            metadata=EvaluationMetadata(
                model=self.provider.label,
                processing_time_ms=run.elapsed_ms,
                token_usage=EvaluationTokenUsage(
                    input_tokens=usage.input_tokens if usage else 0,
                    output_tokens=usage.output_tokens if usage else 0,
                ),
            ),
        )

    # --- lifecycle -----------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the Knowledge Graph client this evaluator built.

        An injected client is the caller's to close: it may outlive this evaluator and be
        shared with others.
        """
        if self._injected_knowledge_graph is None:
            await self._knowledge_graph.aclose()


__all__ = [
    "BatchedLCEvaluation",
    "LCEvaluation",
    "LearningComponentResult",
    "MathStandardsAlignmentEvaluator",
    "MathStandardsAlignmentResult",
]
