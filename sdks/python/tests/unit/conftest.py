"""Shared fakes for the evaluator tests: a recording provider in place of the vendor SDKs."""

from __future__ import annotations

from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest
from pydantic import BaseModel

from learning_commons_evaluators.dependencies.knowledge_graph import (
    AcademicStandard,
    KnowledgeGraphClient,
    LearningComponent,
    LearningComponentSet,
    StandardMatch,
)
from learning_commons_evaluators.errors import StandardNotFoundError
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    BatchedLCEvaluation,
    LCEvaluation,
)
from learning_commons_evaluators.providers import (
    LLMResponse,
    Message,
    ProviderConfig,
    TextGenerationResponse,
    TokenUsage,
    provider_label,
)
from learning_commons_evaluators.schemas.kg_taxonomy import (
    DEFAULT_JURISDICTION,
    AcademicSubject,
    GradeLevel,
)


@dataclass
class FakeProvider:
    """An ``LLMProvider`` that returns a scripted payload and records what it was asked."""

    config: ProviderConfig
    payload: Callable[[type[BaseModel]], Any]
    calls: list[dict[str, Any]] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)
    #: What ``generate_text`` answers, for the prose steps of a multi-step contract.
    prose: str = "prose"
    #: Shared with every fake from the same factory, so the run's order survives.
    log: list[dict[str, Any]] = field(default_factory=list)

    def _record(self, call: dict[str, Any]) -> None:
        self.calls.append(call)
        self.log.append(call)

    @property
    def label(self) -> str:
        return provider_label(self.config.type, self.config.model)

    async def generate_structured(
        self,
        messages: Sequence[Message],
        schema: type[BaseModel],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> LLMResponse[Any]:
        self._record({"messages": list(messages), "schema": schema, "temperature": temperature})
        if self.failures:
            raise self.failures.pop(0)
        return LLMResponse(
            data=self.payload(schema),
            model=self.config.model,
            usage=TokenUsage(input_tokens=7, output_tokens=3),
            latency_ms=12,
        )

    async def generate_text(
        self,
        messages: Sequence[Message],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> TextGenerationResponse:
        # Recorded alongside the structured calls, with ``schema`` absent, so a test reads
        # one ordered record of everything the evaluator asked for.
        self._record({"messages": list(messages), "schema": None, "temperature": temperature})
        if self.failures:
            raise self.failures.pop(0)
        return TextGenerationResponse(
            text=self.prose,
            usage=TokenUsage(input_tokens=5, output_tokens=2),
            latency_ms=8,
        )


@dataclass
class ProviderFactory:
    """Stands in for ``create_provider``; hands out fakes and remembers every config."""

    payload: Callable[[type[BaseModel]], Any]
    created: list[FakeProvider] = field(default_factory=list)
    failures: list[BaseException] = field(default_factory=list)
    prose: str = "prose"
    #: Every call made through this factory, in the order the evaluator made them. A
    #: multi-step evaluator spreads its calls over one provider per model, so reading one
    #: provider's own ``calls`` would drop the steps that ran on another.
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, config: ProviderConfig) -> FakeProvider:
        provider = FakeProvider(
            config, self.payload, failures=self.failures, prose=self.prose, log=self.calls
        )
        self.created.append(provider)
        return provider

    @property
    def last(self) -> FakeProvider:
        return self.created[-1]


#: A standard the Knowledge Graph really holds, used wherever a test needs a plausible
#: one: Multi-State (CCSS) ``3.MD.C.7.d`` and the three learning components it carries,
#: verbatim. Nothing here reaches the service — they are real values so that a failing
#: unit test and a failing live test describe the same standard.
STANDARD_UUID = "6ba25656-d7cc-11e8-824f-0242ac160002"
STATEMENT_CODE = "3.MD.C.7.d"
LEARNING_COMPONENTS: tuple[tuple[str, str], ...] = (
    (
        "29c42ed3-da20-5288-a4b1-c72989c97fe4",
        "Find the area of rectilinear figures by decomposing them into non-overlapping "
        "parts and finding the area of each part",
    ),
    (
        "7be9b24a-c5cc-5882-adae-ac60664a1864",
        "Find the area of rectilinear figures in real-world problems by decomposing them "
        "into non-overlapping parts and finding the area of each part",
    ),
    (
        "a997e206-ba00-5087-9ac7-f301f2eb9841",
        "Solve real-world problems involving rectilinear figures",
    ),
)


def sample_for(schema: type[BaseModel]) -> BaseModel:
    """A minimal valid instance of a generated output model, from its JSON schema.

    One schema cannot be answered from its shape alone: Math Standards Alignment sends the
    learning components it wants judged and checks that every one came back, so a sample
    built from the schema would be rejected as a model that ignored what it was asked.
    That case echoes the identifiers :class:`FakeKnowledgeGraph` serves, which is what the
    evaluator will have sent.
    """
    from tests.unit.schemas.test_generated_outputs import sample

    if schema is BatchedLCEvaluation:
        return BatchedLCEvaluation(
            evaluations=[
                LCEvaluation(
                    lc_id=identifier,
                    reasoning="the item asks for exactly this",
                    answer="Yes",
                    feedback="aligned",
                )
                for identifier, _ in LEARNING_COMPONENTS
            ]
        )
    json_schema = schema.model_json_schema()
    return schema.model_validate(sample(json_schema, json_schema.get("$defs", {})))


@pytest.fixture
def providers() -> Iterator[ProviderFactory]:
    """Route every evaluator's provider construction through recording fakes."""
    factory = ProviderFactory(payload=sample_for)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


@dataclass(frozen=True)
class FakeStandard:
    """One standard a :class:`FakeKnowledgeGraph` holds, as all three endpoints see it."""

    case_identifier_uuid: str = STANDARD_UUID
    statement_code: str = STATEMENT_CODE
    grade_level: tuple[GradeLevel, ...] = (GradeLevel.GRADE_3,)
    components: tuple[tuple[str, str], ...] = LEARNING_COMPONENTS
    undescribed_count: int = 0
    #: What the Knowledge Graph says this standard's subject is. ``None`` models both a
    #: standard that states none and one whose subject the SDK's taxonomy does not carry.
    academic_subject: AcademicSubject | None = AcademicSubject.MATHEMATICS


#: Build variants with ``dataclasses.replace``; pass several to a fake to model a code
#: that several standards answer to.
DEFAULT_STANDARD = FakeStandard()


class FakeKnowledgeGraph(KnowledgeGraphClient):
    """A Knowledge Graph client that answers from memory.

    Subclasses the real client so an evaluator that declares one is typed honestly, and
    deliberately does not call its ``__init__``: there is no key to hold and no connection
    pool to open. Every standard it holds answers the same search, which is how a test
    models a reused code; only the three endpoints the evaluator calls are implemented.
    """

    def __init__(self, *standards: FakeStandard) -> None:
        self.standards = standards or (DEFAULT_STANDARD,)
        #: Every search made, as ``(code, jurisdiction, subject)``.
        self.searches: list[tuple[str, str, str | None]] = []
        #: Every UUID read, in order.
        self.requested: list[str] = []
        self.closed = False

    def _standard(self, case_identifier_uuid: str) -> FakeStandard:
        for standard in self.standards:
            if standard.case_identifier_uuid == case_identifier_uuid:
                return standard
        raise AssertionError(f"nothing holds {case_identifier_uuid!r}")

    async def search_standards(
        self,
        statement_code: str,
        *,
        jurisdiction: Any = DEFAULT_JURISDICTION,
        academic_subject: Any = None,
        limit: int = 50,
    ) -> list[StandardMatch]:
        self.searches.append(
            (
                statement_code,
                str(getattr(jurisdiction, "value", jurisdiction)),
                None
                if academic_subject is None
                else str(getattr(academic_subject, "value", academic_subject)),
            )
        )
        if not self.standards:  # pragma: no cover - a fake with nothing is a test bug
            raise StandardNotFoundError(f'Standard not found: "{statement_code}"', statement_code)
        return [
            StandardMatch(
                case_identifier_uuid=standard.case_identifier_uuid,
                statement_code=standard.statement_code,
                normalized_code=statement_code.upper(),
                description="Relate area to the operations of multiplication and addition.",
                jurisdiction=None,
            )
            for standard in self.standards
        ]

    async def get_academic_standard(self, case_identifier_uuid: str) -> AcademicStandard:
        self.requested.append(case_identifier_uuid)
        standard = self._standard(case_identifier_uuid)
        return AcademicStandard(
            case_identifier_uuid=standard.case_identifier_uuid,
            statement_code=standard.statement_code,
            description="Relate area to the operations of multiplication and addition.",
            academic_subject=standard.academic_subject,
            notes=None,
            jurisdiction=None,
            grade_level=standard.grade_level,
        )

    async def get_learning_component_set(self, case_identifier_uuid: str) -> LearningComponentSet:
        self.requested.append(case_identifier_uuid)
        standard = self._standard(case_identifier_uuid)
        return LearningComponentSet(
            components=tuple(
                LearningComponent(identifier=identifier, description=description)
                for identifier, description in standard.components
            ),
            undescribed_count=standard.undescribed_count,
        )

    async def aclose(self) -> None:
        self.closed = True
