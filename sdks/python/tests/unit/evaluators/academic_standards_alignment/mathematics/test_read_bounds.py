"""Reads of one ambiguous code's copies are bounded: at most a fixed number in flight, and none start after a failure."""

import asyncio
from dataclasses import replace
from typing import Any

import pytest

from learning_commons_evaluators.dependencies.knowledge_graph import LearningComponentSet
from learning_commons_evaluators.errors import KnowledgeGraphError
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    _READ_CONCURRENCY,
    MathStandardsAlignmentEvaluator,
)
from tests.unit.conftest import DEFAULT_STANDARD, FakeKnowledgeGraph

QUESTION = "A playground is shaped like an L. What is its total area in square feet?"
COPIES = 30


def copies(count: int, **overrides: Any) -> list[Any]:
    return [
        replace(
            DEFAULT_STANDARD,
            case_identifier_uuid=f"6ba1{i:04d}-d7cc-11e8-824f-0242ac160002",
            **overrides,
        )
        for i in range(count)
    ]


class Tracking(FakeKnowledgeGraph):
    """Counts reads in flight and started, with a delay so reads overlap."""

    def __init__(self, *standards: Any, fail_first: bool = False) -> None:
        super().__init__(*standards)
        self.in_flight = 0
        self.max_in_flight = 0
        self.started = 0
        self.fail_first = fail_first

    async def get_learning_component_set(self, case_identifier_uuid: str) -> LearningComponentSet:
        self.started += 1
        ordinal = self.started
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.01)
            if self.fail_first and ordinal == 1:
                raise KnowledgeGraphError("Knowledge Graph request failed (HTTP 503)")
            return await super().get_learning_component_set(case_identifier_uuid)
        finally:
            self.in_flight -= 1

    async def get_academic_standard(self, case_identifier_uuid: str) -> Any:
        self.started += 1
        self.in_flight += 1
        self.max_in_flight = max(self.max_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.01)
            return await super().get_academic_standard(case_identifier_uuid)
        finally:
            self.in_flight -= 1


def evaluator(knowledge_graph: FakeKnowledgeGraph) -> MathStandardsAlignmentEvaluator:
    return MathStandardsAlignmentEvaluator(
        anthropic_api_key="test-key", knowledge_graph=knowledge_graph
    )


async def test_no_more_than_the_read_concurrency_is_in_flight(providers: Any) -> None:
    knowledge_graph = Tracking(*copies(COPIES, components=()))

    await evaluator(knowledge_graph).evaluate_by_code(
        question=QUESTION, statement_code="3.MD.C.7.d"
    )

    assert knowledge_graph.max_in_flight <= _READ_CONCURRENCY
    assert knowledge_graph.max_in_flight > 1


async def test_no_read_starts_after_a_failure_has_been_raised(providers: Any) -> None:
    knowledge_graph = Tracking(*copies(COPIES, components=()), fail_first=True)

    with pytest.raises(KnowledgeGraphError, match="503"):
        await evaluator(knowledge_graph).evaluate_by_code(
            question=QUESTION, statement_code="3.MD.C.7.d"
        )

    # The reads in flight when the first one failed, plus at most one that acquired the gate as
    # the failing read released it, before the group cancelled the rest.
    assert knowledge_graph.started <= _READ_CONCURRENCY + 1
    assert knowledge_graph.started < COPIES
