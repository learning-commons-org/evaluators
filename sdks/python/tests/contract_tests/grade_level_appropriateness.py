"""Grade Level Appropriateness-specific helpers for contract tests.

Provides:
  - Named case loaders (one function per test case in the TOML).
  - ``gla_notebook_to_sdk_result``: converts the notebook-format expected result
    (raw ``JsonOutputParser`` dict) to the expected ``GradeLevelAppropriatenessResult``
    that the SDK should produce.
"""

from __future__ import annotations

from learning_commons_evaluators.schemas.evaluator import EvaluationExplanation
from learning_commons_evaluators.schemas.grade_level_appropriateness import (
    GradeLevelAnswer,
    GradeLevelAppropriatenessResult,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluationMetadata,
    EvaluatorMaturity,
    EvaluatorMetadata,
    Status,
)

from .loader import ContractCase, load_contract_case

# ---------------------------------------------------------------------------
# Case loaders
# ---------------------------------------------------------------------------


def load_gla_trees_case() -> ContractCase:
    """Load the 'trees' contract test case for the GLA evaluator."""
    return load_contract_case("grade-level-appropriateness", "trees")


# ---------------------------------------------------------------------------
# Result mapper
# ---------------------------------------------------------------------------


def gla_notebook_to_sdk_result(case: ContractCase) -> GradeLevelAppropriatenessResult:
    """Convert ``case.expected_result`` (notebook format) to a ``GradeLevelAppropriatenessResult``.

    The notebook outputs a plain dict from ``JsonOutputParser``; the SDK wraps
    that into ``GradeLevelAppropriatenessResult``.  This function performs the same
    structural mapping the SDK does so tests can assert equality.

    Only ``answer`` and ``explanation`` are compared — ``metadata`` is excluded
    because it contains non-deterministic fields (timing, evaluation ID, etc.).

    Args:
        case: A loaded :class:`~loader.ContractCase` with a populated
            ``expected_result``.

    Returns:
        A ``GradeLevelAppropriatenessResult`` built from the contract's expected output.
        The ``metadata`` field is a minimal placeholder so the object is valid.
    """
    r = case.expected_result
    answer = GradeLevelAnswer.from_score(r["grade"])
    explanation = EvaluationExplanation(
        summary=r["reasoning"],
        details={
            "alternative_grade": r["alternative_grade"],
            "scaffolding_needed": r["scaffolding_needed"],
        },
    )
    placeholder_metadata = EvaluationMetadata(
        evaluator_metadata=EvaluatorMetadata(
            id="grade-level-appropriateness",
            version="0.1",
            name="Grade Level Appropriateness",
            description="Contract-test placeholder metadata (not compared).",
            maturity=EvaluatorMaturity.early_access,
        ),
        evaluation_settings=None,
        input_metadata={},
        status=Status.succeeded,
    )
    return GradeLevelAppropriatenessResult(
        answer=answer,
        explanation=explanation,
        metadata=placeholder_metadata,
    )
