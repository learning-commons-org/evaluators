"""Math Standards Alignment: does an assessment question assess a standard's components?

One model call judges the question against every learning component the Knowledge Graph
holds for one standard, and the payload reports a verdict per component alongside the
aligned and total counts. There is no single score: the contract declares no ``outcome``
block, so :func:`~learning_commons_evaluators.read_outcome` reports ``None`` for this
evaluator, as it does in the TypeScript SDK.

The standard is named the way a teacher names it -- a code, a grade, and the jurisdiction
whose framework the code belongs to -- and resolved to the Knowledge Graph's identity for
it through search. A code is not an identity: the Knowledge Graph holds one copy of a
standard per adopting jurisdiction, each with its own UUID and often its own spelling
(Ohio writes ``3.MD.7`` where Common Core writes ``3.MD.C.7``), and within one framework a
code can be reused across courses. ``jurisdiction`` picks the framework and ``grade``
separates the reuses; see :meth:`MathStandardsAlignmentEvaluator._resolve`.

This is the only evaluator that calls a non-LLM dependency, so it is the only one holding
something to release. Close it when you are done -- ``async with``, :meth:`aclose`, or
:meth:`~learning_commons_evaluators.evaluators.base.BaseEvaluator.close` from sync code.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from learning_commons_evaluators.config import EvaluatorConfig
from learning_commons_evaluators.contracts import load_contract
from learning_commons_evaluators.contracts.loader import ModelSpec, Prompt, Step
from learning_commons_evaluators.dependencies.knowledge_graph import (
    KnowledgeGraphClient,
    LearningComponent,
    StandardMatch,
)
from learning_commons_evaluators.errors import LLMOutputProcessingError
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
from learning_commons_evaluators.schemas.kg_taxonomy import (
    DEFAULT_JURISDICTION,
    AcademicSubject,
)
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

#: The subject every lookup is scoped to. A code like ``3.MD.C.7`` is only unique within
#: one subject's framework.
ACADEMIC_SUBJECT = AcademicSubject.MATHEMATICS

#: What this evaluator accepts. ``question`` and ``jurisdiction`` are the contract's own
#: properties, so their bounds, enum and messages come from the registry rather than from
#: a copy here. ``standard_code`` reuses the contract's ``statement_code`` property under
#: the name this SDK gives it, and ``grade`` is this SDK's, bound to the grades the
#: contract says the evaluator supports.
INPUT_SCHEMA: dict[str, Any] = {
    "properties": {
        "question": CONTRACT.input_schema["properties"]["question"],
        "standard_code": CONTRACT.input_schema["properties"]["statement_code"],
        "grade": {
            "type": "string",
            "description": (
                "Grade the question is written for, as the Knowledge Graph spells it "
                "('K' through '12'). Used to tell apart standards that share a code."
            ),
            "enum": list(CONTRACT.evaluator.supported_grades),
        },
        "jurisdiction": CONTRACT.input_schema["properties"]["jurisdiction"],
    },
    # Jurisdiction is the one input with a sensible default: most callers mean Common
    # Core, and the Knowledge Graph calls that Multi-State.
    "required": ["question", "standard_code", "grade"],
}


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
        description="The Knowledge Graph's own spelling of the code that was resolved, "
        "which is not always the spelling that was passed."
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
                standard_code="3.MD.C.7.d",
                grade="3",
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
        :param standard_code: The standard's code, spelled as its jurisdiction spells it.
        :param grade: The grade the question is written for, ``"K"`` through ``"12"``.
        :param jurisdiction: Whose framework the code belongs to; defaults to
            ``Multi-State``, which is Common Core.

        :raises InputValidationError: an input is missing, unknown, or outside its schema.
        :raises StandardNotFoundError: the code names no standard in that jurisdiction.
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
                values = validate_inputs(raw, INPUT_SCHEMA)
                question = values["question"]
                standard_code = values["standard_code"]
                grade = values["grade"]
                jurisdiction = values.get("jurisdiction", DEFAULT_JURISDICTION.value)
                run.text_length = utf16_length(question)
                run.grade = grade
                self.logger.info(
                    "Starting %s evaluation",
                    self.metadata.label,
                    extra={
                        **context,
                        "standard_code": standard_code,
                        "grade_level": grade,
                        "jurisdiction": jurisdiction,
                        "text_length": run.text_length,
                    },
                )

                standard = await self._resolve(standard_code, jurisdiction, grade, context)
                component_set = await self._knowledge_graph.get_learning_component_set(
                    standard.case_identifier_uuid
                )
                components = component_set.components
                if component_set.undescribed_count:
                    # total_count reports what was judged, so say why it is short of what
                    # the standard holds rather than letting the gap look like a miscount.
                    self.logger.warning(
                        "Standard has %d learning component(s) with no description; "
                        "they cannot be judged and are not counted",
                        component_set.undescribed_count,
                        extra={**context, "statement_code": standard.statement_code},
                    )

                if not components:
                    # Nothing to judge, so nothing to ask: a standard with no authored
                    # components resolves without a model call, and the zero token usage
                    # in the envelope is what says so.
                    self.logger.info(
                        "Standard has no evaluable learning components; no model call made",
                        extra={**context, "statement_code": standard.statement_code},
                    )
                    return self._envelope(
                        MathStandardsAlignmentResult(
                            statement_code=standard.statement_code,
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

                judged = self._verified(components, response.data, standard.statement_code)
                result = MathStandardsAlignmentResult(
                    statement_code=standard.statement_code,
                    learning_components=judged,
                    aligned_count=sum(1 for component in judged if component.aligned),
                    total_count=len(components),
                )
                self.logger.info(
                    "%s evaluation completed successfully",
                    self.metadata.label,
                    extra={
                        **context,
                        "statement_code": standard.statement_code,
                        "grade_level": grade,
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
                        "grade_level": run.grade,
                        "error": type(error).__name__,
                        "processing_time_ms": run.elapsed_ms,
                    },
                )
                # Nothing is re-classified here: the Knowledge Graph client maps its own
                # failures and ``call_with_resampling`` maps the provider's, so anything
                # else reaching this point is a fault in this SDK and wrapping it would
                # name a service that did not fail (spec §6.2).
                raise

    # --- resolving the standard ---------------------------------------------------------

    async def _resolve(
        self, standard_code: str, jurisdiction: str, grade: str, context: dict[str, Any]
    ) -> StandardMatch:
        """The one standard a code names in a jurisdiction, with the grade breaking ties.

        A code is not unique on its own. Within a framework it is reused across courses --
        an integrated pathway and a subject pathway both carry an algebra code -- and the
        Knowledge Graph returns one result per copy. The grade the caller already told us
        separates them, so the extra lookups it costs happen only when a code was
        ambiguous, never on the ordinary path.

        When the grade still leaves more than one, the first is evaluated and the choice
        is logged with what else it could have been: the alternatives are usually the same
        standard authored per course, so failing the evaluation would refuse work that is
        almost certainly correct. What is not acceptable is choosing silently.

        :raises StandardNotFoundError: raised by the search itself when nothing matches.
        """
        matches = await self._knowledge_graph.search_standards(
            standard_code, jurisdiction=jurisdiction, academic_subject=ACADEMIC_SUBJECT
        )
        if len(matches) == 1:
            return matches[0]

        at_grade = await self._at_grade(matches, grade)
        if len(at_grade) == 1:
            self.logger.debug(
                "Statement code matched %d standards; grade %s identifies one",
                len(matches),
                grade,
                extra={**context, "standard_code": standard_code},
            )
            return at_grade[0]

        candidates = at_grade or matches
        chosen = candidates[0]
        self.logger.warning(
            "Statement code %s matched %d standards in %s and %d at grade %s; "
            "evaluating %s. Pass a more specific code, or read the standard you mean "
            "with search_standards() to see the alternatives.",
            standard_code,
            len(matches),
            jurisdiction,
            len(at_grade),
            grade,
            chosen.case_identifier_uuid,
            extra={
                **context,
                "standard_code": standard_code,
                "chosen": chosen.case_identifier_uuid,
                "alternatives": [
                    match.case_identifier_uuid for match in candidates if match is not chosen
                ],
            },
        )
        return chosen

    async def _at_grade(self, matches: Sequence[StandardMatch], grade: str) -> list[StandardMatch]:
        """The matches taught at ``grade``.

        A search result does not carry grades, so each candidate has to be read. Fetched
        together rather than in turn: this runs only for an ambiguous code, and serialising
        a handful of lookups would make the rare path the slow one as well.
        """
        standards = await asyncio.gather(
            *(
                self._knowledge_graph.get_academic_standard(match.case_identifier_uuid)
                for match in matches
            )
        )
        return [
            match
            for match, standard in zip(matches, standards, strict=True)
            if grade in standard.grade_level
        ]

    # --- pieces of the flow ------------------------------------------------------------

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
