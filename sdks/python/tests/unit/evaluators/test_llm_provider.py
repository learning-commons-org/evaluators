"""Bring-your-own-provider (§3, Draft): an injected ``llm_provider`` replaces every adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx2
import openai
import pytest

from learning_commons_evaluators import (
    AuthenticationError,
    ConfigurationError,
    GraphicsComplexityEvaluator,
    ModelOverride,
    Provider,
    ToneAppropriatenessEvaluator,
)
from learning_commons_evaluators.evaluators.academic_standards_alignment.mathematics.math_standards_alignment import (
    MathStandardsAlignmentEvaluator,
)
from learning_commons_evaluators.evaluators.base import BaseEvaluator
from learning_commons_evaluators.providers import ProviderConfig
from tests.conftest import EventSink
from tests.unit.conftest import FakeKnowledgeGraph, FakeProvider, ProviderFactory, sample_for
from tests.unit.telemetry.test_emission import (
    EACH_EVALUATOR,
    evaluate_with,
    fixture_input,
    steps_planned,
)


@dataclass
class PartnerProvider(FakeProvider):
    """A caller's own provider: it labels itself however it likes."""

    name: str = "acme-gateway"

    @property
    def label(self) -> str:
        return self.name


def partner(name: str = "acme-gateway", **fields: Any) -> PartnerProvider:
    # ``config`` only feeds the fake's recorded model id; nothing builds an adapter from it.
    return PartnerProvider(
        ProviderConfig(type=Provider.OPENAI, model="m"), sample_for, name=name, **fields
    )


def construct(evaluator: type[BaseEvaluator], **overrides: Any) -> BaseEvaluator:
    """The evaluator with no vendor key at all, and only its non-LLM credentials."""
    if evaluator is MathStandardsAlignmentEvaluator:
        overrides.setdefault("knowledge_graph", FakeKnowledgeGraph())
    else:
        overrides.update({key: "test-key" for key in evaluator.metadata.required_credentials})
    return evaluator(**overrides)


class TestEveryEvaluatorUsesTheInjectedProvider:
    """Parametrized over the registry, so an evaluator added later cannot build its own."""

    @EACH_EVALUATOR
    @pytest.mark.parametrize("label", ["acme-gateway", "openai:gpt-4o", "custom:acme"])
    async def test_every_step_runs_on_it_and_no_adapter_is_built(
        self,
        providers: ProviderFactory,
        event_sink: EventSink,
        evaluator: type[BaseEvaluator],
        label: str,
    ) -> None:
        injected = partner(name=label)
        inputs = fixture_input(evaluator)
        evaluation = await evaluate_with(construct(evaluator, llm_provider=injected), inputs)

        assert providers.created == []
        # The caller gets their label back as given.
        assert evaluation.metadata.model == label
        [event] = event_sink.events()
        stages = event["metadata"]["stage_details"]
        assert [stage["stage"] for stage in stages] == steps_planned(evaluator, inputs)
        assert len(injected.calls) == len(stages)
        # Telemetry marks it (§3.4), so a label naming a vendor is never counted as one, and
        # marks it whatever it already starts with.
        assert {stage["provider"] for stage in stages} == {f"custom:{label}"}
        assert event["provider"] == f"custom:{label}"


class TestCredentials:
    def test_no_vendor_key_is_required(self, providers: ProviderFactory) -> None:
        evaluator = ToneAppropriatenessEvaluator(llm_provider=partner(), telemetry=False)
        assert evaluator.providers_in_use == ()

    def test_an_ambient_vendor_key_is_ignored_rather_than_rejected(
        self, providers: ProviderFactory
    ) -> None:
        injected = partner()
        evaluator = ToneAppropriatenessEvaluator(
            llm_provider=injected, openai_api_key="sk-unused", telemetry=False
        )
        assert evaluator.provider is injected
        assert providers.created == []

    def test_a_non_llm_credential_is_still_required(self, providers: ProviderFactory) -> None:
        # The injected provider carries LLM auth only; the Knowledge Graph still needs its key.
        with pytest.raises(
            ConfigurationError, match="Missing required credential: learning_commons_api_key"
        ):
            MathStandardsAlignmentEvaluator(llm_provider=partner(), telemetry=False)

    def test_the_non_llm_credential_satisfies_it(self, providers: ProviderFactory) -> None:
        evaluator = MathStandardsAlignmentEvaluator(
            llm_provider=partner(), learning_commons_api_key="lc", telemetry=False
        )
        assert evaluator.providers_in_use == ()


class TestRefusals:
    def test_it_cannot_be_combined_with_a_model_override(self, providers: ProviderFactory) -> None:
        with pytest.raises(
            ConfigurationError, match="Cannot set both llm_provider and model_override"
        ):
            ToneAppropriatenessEvaluator(
                llm_provider=partner(),
                model_override=ModelOverride(provider=Provider.OPENAI, model="gpt-4o"),
                openai_api_key="k",
            )

    @pytest.mark.parametrize(
        "provider",
        [
            pytest.param(object(), id="nothing"),
            pytest.param(partner(name=42), id="label-not-a-string"),  # type: ignore[arg-type]
            pytest.param(
                type("NoText", (), {"label": "x", "generate_structured": print})(),
                id="no-generate-text",
            ),
            pytest.param(
                type("NoStructured", (), {"label": "x", "generate_text": print})(),
                id="no-generate-structured",
            ),
        ],
    )
    def test_an_object_that_is_not_a_provider_is_refused_at_construction(
        self, providers: ProviderFactory, provider: Any
    ) -> None:
        with pytest.raises(ConfigurationError, match="must implement the LLMProvider interface"):
            ToneAppropriatenessEvaluator(llm_provider=provider)

    def test_an_image_evaluator_refuses_one_without_attachment_support(
        self, providers: ProviderFactory
    ) -> None:
        with pytest.raises(
            ConfigurationError,
            match='provider "acme-gateway" does not declare support for attachments',
        ):
            GraphicsComplexityEvaluator(llm_provider=partner(supports_attachments=False))


class TestAttribution:
    @staticmethod
    def unauthorized() -> openai.APIStatusError:
        response = httpx2.Response(401, request=httpx2.Request("POST", "https://x"))
        return openai.APIStatusError("nope", response=response, body=None)

    @EACH_EVALUATOR
    @pytest.mark.parametrize("label", ["acme-gateway", "openai:gpt-4o"])
    async def test_its_failures_report_custom_with_its_whole_label(
        self, providers: ProviderFactory, evaluator: type[BaseEvaluator], label: str
    ) -> None:
        # §6: ``custom`` whatever the label says, so a caller who names their client after
        # one of our vendors is not reported as that vendor's outage.
        injected = partner(name=label, failures=[self.unauthorized()])
        with pytest.raises(AuthenticationError) as exc_info:
            await evaluate_with(
                construct(evaluator, llm_provider=injected, telemetry=False),
                fixture_input(evaluator),
            )
        assert exc_info.value.dependency == "custom"
        assert exc_info.value.model == label

    @EACH_EVALUATOR
    async def test_a_failed_evaluation_still_reports_it_marked(
        self, providers: ProviderFactory, event_sink: EventSink, evaluator: type[BaseEvaluator]
    ) -> None:
        injected = partner(name="openai:gpt-4o", failures=[self.unauthorized()])
        with pytest.raises(AuthenticationError):
            await evaluate_with(
                construct(evaluator, llm_provider=injected), fixture_input(evaluator)
            )
        [event] = event_sink.events()
        assert event["status"] == "error"
        assert event["provider"] == "custom:openai:gpt-4o"


class TestBuiltInAdaptersAreUnmarked:
    @EACH_EVALUATOR
    async def test_telemetry_names_them_by_their_own_label(
        self, providers: ProviderFactory, event_sink: EventSink, evaluator: type[BaseEvaluator]
    ) -> None:
        keys = {f"{p.value}_api_key": "k" for p in evaluator.metadata.default_providers}
        evaluation = await evaluate_with(construct(evaluator, **keys), fixture_input(evaluator))
        [event] = event_sink.events()
        labels = {stage["provider"] for stage in event["metadata"]["stage_details"]}
        assert labels == {fake.label for fake in providers.created if fake.calls}
        assert not any(label.startswith("custom:") for label in labels)
        assert evaluation.metadata.model.split("+")[0] in labels
