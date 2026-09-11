"""The error taxonomy's shape and retryability rules (SDK spec §6.1–§6.3).

Mirrors the ``retryable is data`` and ``taxonomy shape`` suites of the TypeScript SDK's
``wrap-provider-error.test.ts`` so both SDKs are held to the same rules.
"""

from __future__ import annotations

import pytest

from learning_commons_evaluators.errors import (
    AuthenticationError,
    ConfigurationError,
    DependencyError,
    EvaluationError,
    EvaluatorError,
    InputValidationError,
    KnowledgeGraphError,
    LLMOutputProcessingError,
    LLMProviderError,
    NetworkError,
    RateLimitError,
    RequestTimeoutError,
    StandardNotFoundError,
)


class TestRetryableIsData:
    def test_false_for_caller_faults(self) -> None:
        assert ConfigurationError("x").retryable is False
        assert InputValidationError("x").retryable is False
        assert StandardNotFoundError("x", "4.OA.A.1").retryable is False

    def test_true_for_output_processing_which_resamples(self) -> None:
        assert LLMOutputProcessingError("bad shape").retryable is True

    def test_follows_class_default_for_dependency_failures(self) -> None:
        assert AuthenticationError("x", dependency="openai").retryable is False
        assert RateLimitError("x", dependency="openai").retryable is True
        assert NetworkError("x", dependency="openai").retryable is True
        assert RequestTimeoutError("x", dependency="openai").retryable is True

    def test_catch_alls_retryable_only_on_5xx(self) -> None:
        assert LLMProviderError("x", dependency="openai", status_code=503).retryable is True
        assert LLMProviderError("x", dependency="openai", status_code=400).retryable is False
        assert LLMProviderError("x", dependency="openai").retryable is False
        assert KnowledgeGraphError("x", status_code=500).retryable is True
        assert KnowledgeGraphError("x", status_code=404).retryable is False

    def test_explicit_override_wins_over_5xx_rule_and_class_default(self) -> None:
        assert (
            LLMProviderError("x", dependency="openai", status_code=503, retryable=False).retryable
            is False
        )
        assert AuthenticationError("x", dependency="openai", retryable=True).retryable is True


class TestTaxonomyShape:
    def test_bad_standards_code_is_the_callers_fault(self) -> None:
        err = StandardNotFoundError("unknown code", "9.ZZ.Z.9")
        assert isinstance(err, InputValidationError)
        assert not isinstance(err, DependencyError)
        assert err.statement_code == "9.ZZ.Z.9"

    def test_every_external_failure_is_a_dependency_error(self) -> None:
        for err in (
            AuthenticationError("x", dependency="openai"),
            RateLimitError("x", dependency="google"),
            NetworkError("x", dependency="anthropic"),
            RequestTimeoutError("x", dependency="openai"),
            LLMProviderError("x", dependency="openai"),
            KnowledgeGraphError("x"),
        ):
            assert isinstance(err, DependencyError)
            assert isinstance(err, EvaluatorError)

    def test_output_processing_is_an_evaluation_error_not_a_dependency_error(self) -> None:
        err = LLMOutputProcessingError("x")
        assert isinstance(err, EvaluationError)
        assert not isinstance(err, DependencyError)

    def test_knowledge_graph_dependency_is_fixed(self) -> None:
        assert KnowledgeGraphError("x").dependency == "knowledge-graph"

    @pytest.mark.parametrize("abstract", [EvaluatorError, EvaluationError, DependencyError])
    def test_abstract_bases_cannot_be_instantiated(self, abstract: type) -> None:
        with pytest.raises(TypeError, match="abstract"):
            if abstract is DependencyError:
                abstract("x", False, dependency="openai")
            else:
                abstract("x", False)

    def test_class_name_is_the_canonical_error_code(self) -> None:
        # There is no ``name`` mirror: the class is the identity, so the code is its name.
        assert type(RateLimitError("x", dependency="openai")).__name__ == "RateLimitError"
        assert type(KnowledgeGraphError("x")).__name__ == "KnowledgeGraphError"

    def test_str_is_the_message(self) -> None:
        assert str(ConfigurationError("missing key")) == "missing key"

    def test_rate_limit_exposes_retry_after_ms(self) -> None:
        assert RateLimitError("x", dependency="openai", retry_after_ms=2500).retry_after_ms == 2500
        assert RateLimitError("x", dependency="openai").retry_after_ms is None

    def test_rate_limit_defaults_to_429_but_lets_the_provider_status_win(self) -> None:
        assert RateLimitError("x", dependency="openai").status_code == 429
        assert RateLimitError("x", dependency="openai", status_code=None).status_code == 429
        assert RateLimitError("x", dependency="openai", status_code=529).status_code == 529

    def test_validation_errors_on_output_processing_failures(self) -> None:
        details = [{"loc": ("evaluations",), "type": "missing"}]
        assert LLMOutputProcessingError("x", details).validation_errors == details
        assert LLMOutputProcessingError("x").validation_errors is None

    def test_dependency_fields_default_to_none(self) -> None:
        err = LLMProviderError("x", dependency="google")
        assert err.status_code is None
        assert err.request_id is None
        assert err.model is None

    def test_cause_travels_on_dunder_cause(self) -> None:
        original = ValueError("upstream")
        err = ConfigurationError("x", original)
        assert err.__cause__ is original
        assert LLMProviderError("x", dependency="openai", cause=original).__cause__ is original
