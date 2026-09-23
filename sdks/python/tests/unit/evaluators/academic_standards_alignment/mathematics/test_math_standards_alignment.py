"""Math Standards Alignment: what it accepts, how it resolves a code, and what it reports.

The Knowledge Graph is injected rather than mocked at the transport, so these tests are
about the evaluator: the client's own behaviour against the wire is covered in
``tests/unit/dependencies/test_knowledge_graph.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from typing import Any
from unittest.mock import patch

import pytest

from learning_commons_evaluators import (
    ConfigurationError,
    InputValidationError,
    LLMOutputProcessingError,
    StandardNotFoundError,
    read_outcome,
)
from learning_commons_evaluators.errors import RateLimitError
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    BatchedLCEvaluation,
    LCEvaluation,
    MathStandardsAlignmentEvaluator,
)
from learning_commons_evaluators.schemas.kg_taxonomy import GradeLevel
from tests.unit.conftest import (
    DEFAULT_STANDARD,
    LEARNING_COMPONENTS,
    STANDARD_UUID,
    STATEMENT_CODE,
    FakeKnowledgeGraph,
    ProviderFactory,
)

QUESTION = "A playground is shaped like an L. What is its total area in square feet?"
#: A second copy of the same code, as a jurisdiction that reuses codes across courses
#: would return alongside the first.
OTHER_UUID = "6ba04403-d7cc-11e8-824f-0242ac160002"


def build(
    knowledge_graph: FakeKnowledgeGraph | None = None, **overrides: Any
) -> MathStandardsAlignmentEvaluator:
    return MathStandardsAlignmentEvaluator(
        anthropic_api_key="test-key",
        knowledge_graph=knowledge_graph if knowledge_graph is not None else FakeKnowledgeGraph(),
        **overrides,
    )


def answers(*entries: tuple[str, str]) -> BatchedLCEvaluation:
    """A model answer judging each identifier with the given verdict."""
    return BatchedLCEvaluation(
        evaluations=[
            LCEvaluation(
                lc_id=identifier,
                reasoning=f"reasoning for {identifier}",
                answer=answer,  # type: ignore[arg-type]
                feedback=f"feedback for {identifier}",
            )
            for identifier, answer in entries
        ]
    )


ALL_ALIGNED = answers(*[(identifier, "Yes") for identifier, _ in LEARNING_COMPONENTS])


@dataclass
class Script:
    """What the model will answer, which a test reassigns before evaluating."""

    answer: BatchedLCEvaluation = field(default_factory=lambda: ALL_ALIGNED)


@pytest.fixture
def script() -> Script:
    return Script()


@pytest.fixture
def providers(script: Script) -> Iterator[ProviderFactory]:
    """The shared recording fake, answering whatever ``script`` currently holds."""
    factory = ProviderFactory(payload=lambda _schema: script.answer)
    with patch("learning_commons_evaluators.evaluators.base.create_provider", factory):
        yield factory


class TestConstruction:
    def test_a_missing_learning_commons_key_is_refused_before_any_call(self) -> None:
        # §3.1, and the reason it matters here: the Knowledge Graph is reached before the
        # model is, so a missing key that surfaced mid-evaluation would already have cost
        # the caller a request.
        with pytest.raises(
            ConfigurationError, match="Missing required credential: learning_commons_api_key"
        ):
            MathStandardsAlignmentEvaluator(anthropic_api_key="test-key")

    def test_a_missing_provider_key_is_refused(self) -> None:
        with pytest.raises(ConfigurationError, match="anthropic_api_key"):
            MathStandardsAlignmentEvaluator(learning_commons_api_key="test-key")

    def test_an_injected_client_carries_its_own_credential(self) -> None:
        evaluator = MathStandardsAlignmentEvaluator(
            anthropic_api_key="test-key", knowledge_graph=FakeKnowledgeGraph()
        )
        assert evaluator.metadata.required_credentials == ("learning_commons_api_key",)

    async def test_it_leaves_an_injected_client_alone(self) -> None:
        injected = FakeKnowledgeGraph()
        await build(injected).aclose()
        assert not injected.closed, "an injected client may outlive the evaluator"

    async def test_it_closes_the_client_it_built(self) -> None:
        # The one evaluator holding a connection pool, so the one whose close does work.
        evaluator = MathStandardsAlignmentEvaluator(
            anthropic_api_key="test-key", learning_commons_api_key="test-key"
        )
        pool = evaluator._knowledge_graph._client.get_async_httpx_client()

        await evaluator.aclose()

        assert pool.is_closed


class TestInputs:
    @pytest.mark.parametrize(
        ("inputs", "expected"),
        [
            ({"statement_code": STATEMENT_CODE, "grade": "3"}, "question is required"),
            ({"question": QUESTION, "grade": "3"}, "statement_code is required"),
            (
                {"question": "  ", "statement_code": STATEMENT_CODE, "grade": "3"},
                "cannot be empty",
            ),
            (
                {"question": "x" * 10001, "statement_code": STATEMENT_CODE, "grade": "3"},
                "too long",
            ),
            (
                {"question": QUESTION, "statement_code": "x" * 51, "grade": "3"},
                "too long",
            ),
            (
                {"question": QUESTION, "statement_code": STATEMENT_CODE, "grade": "13"},
                "Invalid grade",
            ),
            (
                {
                    "question": QUESTION,
                    "statement_code": STATEMENT_CODE,
                    "grade": "3",
                    "jurisdiction": "Atlantis",
                },
                "Invalid jurisdiction",
            ),
        ],
    )
    async def test_it_enforces_the_declared_bounds(
        self, providers: ProviderFactory, inputs: dict[str, str], expected: str
    ) -> None:
        with pytest.raises(InputValidationError, match=expected):
            await build().evaluate(**inputs)

    async def test_it_rejects_an_unknown_input(self, providers: ProviderFactory) -> None:
        with pytest.raises(InputValidationError, match="Unknown input"):
            await build().evaluate(
                question=QUESTION, statement_code=STATEMENT_CODE, case_identifier_uuid=STANDARD_UUID
            )

    async def test_the_contracts_inputs_are_a_valid_call(self, providers: ProviderFactory) -> None:
        # The superset property, from the caller's side: what the registry declares, under
        # the registry's names, with no grade.
        knowledge_graph = FakeKnowledgeGraph()
        evaluation = await build(knowledge_graph).evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, jurisdiction="Multi-State"
        )
        assert evaluation.result.total_count == 3
        assert knowledge_graph.searches == [(STATEMENT_CODE, "Multi-State", "Mathematics")]

    async def test_a_grade_passed_as_an_integer_is_accepted(
        self, providers: ProviderFactory
    ) -> None:
        # §2.3: the idiomatic Python convenience, normalised to the contract's token.
        knowledge_graph = FakeKnowledgeGraph()
        await build(knowledge_graph).evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade=3
        )
        assert knowledge_graph.searches

    async def test_jurisdiction_defaults_to_common_core(self, providers: ProviderFactory) -> None:
        knowledge_graph = FakeKnowledgeGraph()
        await build(knowledge_graph).evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )
        assert knowledge_graph.searches == [(STATEMENT_CODE, "Multi-State", "Mathematics")]

    async def test_the_jurisdiction_given_is_the_one_searched(
        self, providers: ProviderFactory
    ) -> None:
        knowledge_graph = FakeKnowledgeGraph()
        await build(knowledge_graph).evaluate(
            question=QUESTION, statement_code="3.MD.7", grade="3", jurisdiction="Ohio"
        )
        assert knowledge_graph.searches == [("3.MD.7", "Ohio", "Mathematics")]


class TestResolvingTheCode:
    async def test_one_match_is_used_without_reading_the_standard(
        self, providers: ProviderFactory
    ) -> None:
        # The search result already carries the code, so the ordinary path costs one
        # search and one component fetch, and never reads the standard itself.
        knowledge_graph = FakeKnowledgeGraph()
        await build(knowledge_graph).evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )
        assert knowledge_graph.requested == [STANDARD_UUID]

    async def test_a_code_that_names_nothing_raises(self, providers: ProviderFactory) -> None:
        class Empty(FakeKnowledgeGraph):
            async def search_standards(self, statement_code: str, **_: Any) -> list[Any]:
                raise StandardNotFoundError(
                    f'Standard not found: "{statement_code}"', statement_code
                )

        with pytest.raises(StandardNotFoundError):
            await build(Empty()).evaluate(question=QUESTION, statement_code="9.99.Z", grade="3")

    async def test_the_grade_picks_between_standards_sharing_a_code(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        eighth_grade = replace(
            DEFAULT_STANDARD,
            case_identifier_uuid=OTHER_UUID,
            grade_level=(GradeLevel.GRADE_8,),
        )
        knowledge_graph = FakeKnowledgeGraph(eighth_grade, DEFAULT_STANDARD)

        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            await build(knowledge_graph).evaluate(
                question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
            )

        # Both candidates were read to find their grades, then only the grade-3 one's
        # components were fetched — and the choice needed no warning.
        assert knowledge_graph.requested == [OTHER_UUID, STANDARD_UUID, STANDARD_UUID]
        assert not [record for record in caplog.records if record.levelno == logging.WARNING]

    async def test_a_tie_the_grade_cannot_break_is_chosen_out_loud(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Two copies of the same standard at the same grade, as an integrated pathway and
        # a subject pathway both authoring it would give.
        twin = replace(DEFAULT_STANDARD, case_identifier_uuid=OTHER_UUID)
        knowledge_graph = FakeKnowledgeGraph(DEFAULT_STANDARD, twin)

        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluation = await build(knowledge_graph).evaluate(
                question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
            )

        [warning] = [record for record in caplog.records if record.levelno == logging.WARNING]
        assert "matched 2 standards" in warning.getMessage()
        assert STANDARD_UUID in warning.getMessage()
        assert getattr(warning, "alternatives") == [OTHER_UUID]  # noqa: B009 — a log extra
        # Evaluated rather than refused: the alternatives are the same standard authored
        # twice, so refusing would turn a near-certain answer into a failure.
        assert evaluation.result.total_count == 3

    async def test_an_ambiguous_code_with_no_grade_is_chosen_out_loud(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        # Grade is optional, so it is not always there to break the tie; the warning then
        # says what would have.
        twin = replace(DEFAULT_STANDARD, case_identifier_uuid=OTHER_UUID)
        knowledge_graph = FakeKnowledgeGraph(DEFAULT_STANDARD, twin)

        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            await build(knowledge_graph).evaluate(question=QUESTION, statement_code=STATEMENT_CODE)

        [warning] = [record for record in caplog.records if record.levelno == logging.WARNING]
        assert "no grade was given" in warning.getMessage()
        # Nothing was read to compare grades, because there was no grade to compare to.
        assert knowledge_graph.requested == [STANDARD_UUID]

    async def test_a_grade_matching_no_candidate_falls_back_and_says_so(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        eighth = replace(DEFAULT_STANDARD, grade_level=(GradeLevel.GRADE_8,))
        ninth = replace(
            DEFAULT_STANDARD,
            case_identifier_uuid=OTHER_UUID,
            grade_level=(GradeLevel.GRADE_9,),
        )
        knowledge_graph = FakeKnowledgeGraph(eighth, ninth)

        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluation = await build(knowledge_graph).evaluate(
                question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
            )

        [warning] = [record for record in caplog.records if record.levelno == logging.WARNING]
        assert "0 at grade 3" in warning.getMessage()
        assert evaluation.result.total_count == 3


class TestEvaluate:
    async def test_it_judges_every_learning_component_the_standard_carries(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build().evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )

        result = evaluation.result
        assert result.statement_code == STATEMENT_CODE
        assert [component.identifier for component in result.learning_components] == [
            identifier for identifier, _ in LEARNING_COMPONENTS
        ]
        assert result.aligned_count == 3
        assert result.total_count == 3

    async def test_the_payload_carries_the_knowledge_graphs_spelling_of_the_code(
        self, providers: ProviderFactory
    ) -> None:
        # The caller's spelling is a lookup key; what comes back is the canonical one, and
        # that is what a report joins on.
        evaluation = await build().evaluate(
            question=QUESTION, statement_code="3.md.c.7.d", grade="3"
        )
        assert evaluation.result.statement_code == STATEMENT_CODE

    async def test_aligned_count_reflects_the_verdicts_rather_than_the_component_count(
        self, providers: ProviderFactory, script: Script
    ) -> None:
        identifiers = [identifier for identifier, _ in LEARNING_COMPONENTS]
        script.answer = answers(
            (identifiers[0], "Yes"), (identifiers[1], "No"), (identifiers[2], "No")
        )

        evaluation = await build().evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )

        assert evaluation.result.aligned_count == 1
        assert evaluation.result.total_count == 3
        assert [c.aligned for c in evaluation.result.learning_components] == [True, False, False]

    async def test_it_wraps_the_payload_in_the_shared_envelope(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build().evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )

        assert evaluation.evaluator == MathStandardsAlignmentEvaluator.metadata.id
        assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"
        assert evaluation.metadata.processing_time_ms >= 0
        assert evaluation.metadata.token_usage.input_tokens > 0

    async def test_it_reports_no_single_score(self, providers: ProviderFactory) -> None:
        # As in TypeScript: the contract declares no outcome, so there is no field a
        # report can read as this evaluation's verdict.
        evaluation = await build().evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )
        assert (
            read_outcome(evaluation, MathStandardsAlignmentEvaluator.metadata.outcome).score is None
        )

    async def test_it_sends_the_question_and_every_component_to_the_model(
        self, providers: ProviderFactory
    ) -> None:
        await build().evaluate(question=QUESTION, statement_code=STATEMENT_CODE, grade="3")

        [call] = providers.calls
        prompt = "\n".join(message["content"] for message in call["messages"])
        assert QUESTION in prompt
        for position, (identifier, description) in enumerate(LEARNING_COMPONENTS, start=1):
            assert f"{position}. [{identifier}] {description}" in prompt
        assert call["temperature"] == 0
        assert call["schema"] is BatchedLCEvaluation


class TestStandardsWithNothingToJudge:
    async def test_a_standard_with_no_components_resolves_without_a_model_call(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build(
            FakeKnowledgeGraph(replace(DEFAULT_STANDARD, components=()))
        ).evaluate(question=QUESTION, statement_code=STATEMENT_CODE, grade="3")

        assert providers.calls == []
        assert evaluation.result.learning_components == []
        assert evaluation.result.aligned_count == 0
        assert evaluation.result.total_count == 0
        # Zero tokens is what says no model answered; the label still names the model that
        # would have.
        assert evaluation.metadata.token_usage.input_tokens == 0
        assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"

    async def test_components_without_descriptions_are_counted_out_loud(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        # total_count reports what was judged, so a standard whose components carry no
        # text to judge must not look like a miscount.
        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluation = await build(
                FakeKnowledgeGraph(replace(DEFAULT_STANDARD, undescribed_count=2))
            ).evaluate(question=QUESTION, statement_code=STATEMENT_CODE, grade="3")

        assert evaluation.result.total_count == 3
        assert any("no description" in record.getMessage() for record in caplog.records)


class TestTheModelsAnswerIsVerified:
    async def test_a_component_the_model_skipped_fails_the_evaluation(
        self, providers: ProviderFactory, script: Script
    ) -> None:
        # Not reported as unaligned: nothing was measured for it, and `aligned: false`
        # would read as a judgement that the question does not assess it.
        identifiers = [identifier for identifier, _ in LEARNING_COMPONENTS]
        script.answer = answers((identifiers[0], "Yes"))

        with pytest.raises(LLMOutputProcessingError) as raised:
            await build().evaluate(question=QUESTION, statement_code=STATEMENT_CODE, grade="3")

        assert identifiers[1] in str(raised.value)
        assert identifiers[2] in str(raised.value)
        assert STATEMENT_CODE in str(raised.value)
        assert raised.value.retryable

    async def test_a_verdict_for_something_never_sent_is_dropped(
        self, providers: ProviderFactory, script: Script
    ) -> None:
        script.answer = answers(
            *[(identifier, "Yes") for identifier, _ in LEARNING_COMPONENTS],
            ("lc-the-model-invented", "Yes"),
        )

        evaluation = await build().evaluate(
            question=QUESTION, statement_code=STATEMENT_CODE, grade="3"
        )

        assert len(evaluation.result.learning_components) == 3
        assert all(
            component.identifier != "lc-the-model-invented"
            for component in evaluation.result.learning_components
        )

    async def test_a_provider_failure_is_raised_as_it_was_classified(
        self, providers: ProviderFactory
    ) -> None:
        providers.failures.append(RateLimitError("slow down", dependency="anthropic"))
        with pytest.raises(RateLimitError):
            await build().evaluate(question=QUESTION, statement_code=STATEMENT_CODE, grade="3")
