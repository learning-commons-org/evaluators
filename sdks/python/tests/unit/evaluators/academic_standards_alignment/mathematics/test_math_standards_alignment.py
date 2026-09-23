"""Math Standards Alignment: what it accepts, what it asks the model, and what it reports.

The Knowledge Graph is injected rather than mocked at the transport, so these tests are
about the evaluator: the client's own behaviour against the wire is covered in
``tests/unit/dependencies/test_knowledge_graph.py``.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import patch

import pytest

from learning_commons_evaluators import (
    ConfigurationError,
    InputValidationError,
    LLMOutputProcessingError,
    read_outcome,
)
from learning_commons_evaluators.errors import RateLimitError
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    BatchedLCEvaluation,
    LCEvaluation,
    MathStandardsAlignmentEvaluator,
)
from tests.unit.conftest import (
    LEARNING_COMPONENTS,
    STANDARD_UUID,
    STATEMENT_CODE,
    FakeKnowledgeGraph,
    ProviderFactory,
)

QUESTION = "A playground is shaped like an L. What is its total area in square feet?"


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

    def test_a_learning_commons_key_alone_builds_its_own_client(self) -> None:
        evaluator = MathStandardsAlignmentEvaluator(
            anthropic_api_key="test-key", learning_commons_api_key="test-key"
        )
        assert evaluator._injected_knowledge_graph is None

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
    async def test_it_names_the_deferred_contract_inputs_rather_than_calling_them_unknown(
        self, providers: ProviderFactory
    ) -> None:
        # The registry still declares statement_code + jurisdiction and TypeScript still
        # takes them, so a caller reading the contract will try them here (DSCR-2252).
        with pytest.raises(InputValidationError, match="statement_code, jurisdiction"):
            await build().evaluate(
                question=QUESTION, statement_code="3.MD.C.7.d", jurisdiction="Multi-State"
            )

    async def test_it_rejects_an_unknown_input(self, providers: ProviderFactory) -> None:
        with pytest.raises(InputValidationError, match="Unknown input"):
            await build().evaluate(question=QUESTION, standard="3.MD.C.7.d")

    @pytest.mark.parametrize(
        ("inputs", "expected"),
        [
            ({"case_identifier_uuid": STANDARD_UUID}, "question is required"),
            ({"question": QUESTION}, "case_identifier_uuid is required"),
            ({"question": "  ", "case_identifier_uuid": STANDARD_UUID}, "cannot be empty"),
            (
                {"question": "x" * 10001, "case_identifier_uuid": STANDARD_UUID},
                "too long",
            ),
        ],
    )
    async def test_it_enforces_the_declared_bounds(
        self, providers: ProviderFactory, inputs: dict[str, str], expected: str
    ) -> None:
        with pytest.raises(InputValidationError, match=expected):
            await build().evaluate(**inputs)

    async def test_a_malformed_uuid_is_refused_before_any_request(
        self, providers: ProviderFactory
    ) -> None:
        knowledge_graph = FakeKnowledgeGraph()
        with pytest.raises(InputValidationError, match="must be a CASE Network UUID"):
            await build(knowledge_graph).evaluate(
                question=QUESTION, case_identifier_uuid="3.MD.C.7.d"
            )
        assert knowledge_graph.requested == []


class TestEvaluate:
    async def test_it_judges_every_learning_component_the_standard_carries(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

        result = evaluation.result
        assert result.statement_code == STATEMENT_CODE
        assert [component.identifier for component in result.learning_components] == [
            identifier for identifier, _ in LEARNING_COMPONENTS
        ]
        assert [component.description for component in result.learning_components] == [
            description for _, description in LEARNING_COMPONENTS
        ]
        assert result.aligned_count == 3
        assert result.total_count == 3

    async def test_aligned_count_reflects_the_verdicts_rather_than_the_component_count(
        self, providers: ProviderFactory, script: Script
    ) -> None:
        identifiers = [identifier for identifier, _ in LEARNING_COMPONENTS]
        script.answer = answers(
            (identifiers[0], "Yes"), (identifiers[1], "No"), (identifiers[2], "No")
        )

        evaluation = await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

        assert evaluation.result.aligned_count == 1
        assert evaluation.result.total_count == 3
        assert [c.aligned for c in evaluation.result.learning_components] == [True, False, False]

    async def test_it_wraps_the_payload_in_the_shared_envelope(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

        assert evaluation.evaluator == MathStandardsAlignmentEvaluator.metadata.id
        assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"
        assert evaluation.metadata.processing_time_ms >= 0
        assert evaluation.metadata.token_usage.input_tokens > 0

    async def test_it_reports_no_single_score(self, providers: ProviderFactory) -> None:
        # As in TypeScript: the contract declares no outcome, so there is no field a
        # report can read as this evaluation's verdict.
        evaluation = await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)
        assert (
            read_outcome(evaluation, MathStandardsAlignmentEvaluator.metadata.outcome).score is None
        )

    async def test_it_sends_the_question_and_every_component_to_the_model(
        self, providers: ProviderFactory
    ) -> None:
        await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

        [call] = providers.calls
        prompt = "\n".join(message["content"] for message in call["messages"])
        assert QUESTION in prompt
        for position, (identifier, description) in enumerate(LEARNING_COMPONENTS, start=1):
            assert f"{position}. [{identifier}] {description}" in prompt
        assert call["temperature"] == 0
        assert call["schema"] is BatchedLCEvaluation

    async def test_it_fetches_the_standard_and_its_components_by_the_uuid_given(
        self, providers: ProviderFactory
    ) -> None:
        knowledge_graph = FakeKnowledgeGraph()
        await build(knowledge_graph).evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)
        assert knowledge_graph.requested == [STANDARD_UUID, STANDARD_UUID]


class TestStandardsWithNothingToJudge:
    async def test_a_standard_with_no_components_resolves_without_a_model_call(
        self, providers: ProviderFactory
    ) -> None:
        evaluation = await build(FakeKnowledgeGraph(components=())).evaluate(
            question=QUESTION, case_identifier_uuid=STANDARD_UUID
        )

        assert providers.calls == []
        assert evaluation.result.learning_components == []
        assert evaluation.result.aligned_count == 0
        assert evaluation.result.total_count == 0
        # Zero tokens is what says no model answered; the label still names the model that
        # would have.
        assert evaluation.metadata.token_usage.input_tokens == 0
        assert evaluation.metadata.token_usage.output_tokens == 0
        assert evaluation.metadata.model == "anthropic:claude-haiku-4-5-20251001"

    async def test_components_without_descriptions_are_counted_out_loud(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        # total_count reports what was judged, so a standard whose components carry no
        # text to judge must not look like a miscount.
        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluation = await build(FakeKnowledgeGraph(undescribed_count=2)).evaluate(
                question=QUESTION, case_identifier_uuid=STANDARD_UUID
            )

        assert evaluation.result.total_count == 3
        assert any("no description" in record.getMessage() for record in caplog.records)

    async def test_a_standard_with_no_code_reports_an_empty_one_and_says_so(
        self, providers: ProviderFactory, caplog: pytest.LogCaptureFixture
    ) -> None:
        with caplog.at_level(logging.WARNING, logger="learning_commons_evaluators"):
            evaluation = await build(FakeKnowledgeGraph(statement_code=None)).evaluate(
                question=QUESTION, case_identifier_uuid=STANDARD_UUID
            )

        assert evaluation.result.statement_code == ""
        assert any("no statement code" in record.getMessage() for record in caplog.records)


class TestTheModelsAnswerIsVerified:
    async def test_a_component_the_model_skipped_fails_the_evaluation(
        self, providers: ProviderFactory, script: Script
    ) -> None:
        # Not reported as unaligned: nothing was measured for it, and `aligned: false`
        # would read as a judgement that the question does not assess it.
        identifiers = [identifier for identifier, _ in LEARNING_COMPONENTS]
        script.answer = answers((identifiers[0], "Yes"))

        with pytest.raises(LLMOutputProcessingError) as raised:
            await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

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

        evaluation = await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)

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
            await build().evaluate(question=QUESTION, case_identifier_uuid=STANDARD_UUID)
