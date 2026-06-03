"""Conventionality-specific helpers for contract tests.

Provides:
  - Named case loaders (one function per test case in the TOML).
  - ``conventionality_notebook_to_sdk_result``: converts the notebook-format
    expected result (raw ``JsonOutputParser`` dict) to the expected
    ``TextComplexityResult`` that the SDK should produce.
"""

from __future__ import annotations

from learning_commons_evaluators.schemas.evaluator import EvaluationExplanation
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
)
from learning_commons_evaluators.schemas.text_complexity import (
    TextComplexityAnswer,
    TextComplexityResult,
)

from .loader import ContractCase, load_contract_case

# ---------------------------------------------------------------------------
# Case loaders
# ---------------------------------------------------------------------------


def load_conventionality_turnip_case() -> ContractCase:
    """Load the 'turnip' contract test case for the conventionality evaluator."""
    return load_contract_case("conventionality", "turnip")


# ---------------------------------------------------------------------------
# Result mapper
# ---------------------------------------------------------------------------


def conventionality_notebook_to_sdk_result(case: ContractCase) -> TextComplexityResult:
    """Convert ``case.expected_result`` (notebook format) to a ``TextComplexityResult``.

    The notebook outputs a plain dict from ``JsonOutputParser``; the SDK wraps
    that into ``TextComplexityResult``.  This function performs the same
    structural mapping the SDK does so tests can assert equality.

    Only ``answer`` and ``explanation`` are compared — ``metadata`` is excluded
    because it contains non-deterministic fields (timing, evaluation ID, etc.).

    Args:
        case: A loaded :class:`~loader.ContractCase` with a populated
            ``expected_result``.

    Returns:
        A ``TextComplexityResult`` built from the contract's expected output.
        The ``metadata`` field is a minimal placeholder so the object is valid.
    """
    r = case.expected_result
    answer = TextComplexityAnswer.from_score(r["complexity_score"])
    explanation = EvaluationExplanation(
        summary=r["reasoning"],
        details={
            "conventionality_features": r["conventionality_features"],
            "grade_context": r["grade_context"],
            "instructional_insights": r["instructional_insights"],
        },
    )
    # A minimal metadata object — only used to satisfy the result model; not
    # compared in assertions (use assert_answer / assert_explanation helpers).
    placeholder_metadata = EvaluationMetadata(
        evaluator_metadata=EvaluatorMetadata(
            id="conventionality",
            version="0.1",
            name="Conventionality",
            description="Contract-test placeholder metadata (not compared).",
            maturity=EvaluatorMaturity.early_access,
        ),
        evaluation_settings=None,
        input_metadata={},
        status=Status.succeeded,
    )
    return TextComplexityResult(
        answer=answer,
        explanation=explanation,
        metadata=placeholder_metadata,
    )
