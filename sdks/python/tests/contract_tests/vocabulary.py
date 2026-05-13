"""Vocabulary-specific helpers for contract tests.

Provides:
  - Named case loaders (one function per test case in the TOML).
  - Result mappers: convert the notebook-format expected result (raw
    ``JsonOutputParser`` dict) to the ``TextComplexityResult`` that the SDK
    should produce.

Both grade paths use the same ``Output``-style schema (word-level breakdown +
string ``complexity_score``), so both mappers apply the same normalisation:
  ``complexity_score.lower().replace(" ", "_")`` → ``TextComplexityAnswer``.
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


def load_vocabulary_grade34_case() -> ContractCase:
    """Load the 'marco_polo_grade3' contract test case (grades 3–4 path)."""
    return load_contract_case("vocabulary", "marco_polo_grade3")


def load_vocabulary_other_grades_case() -> ContractCase:
    """Load the 'hurricanes_grade7' contract test case (grades 5–12 path)."""
    return load_contract_case("vocabulary", "hurricanes_grade7")


# ---------------------------------------------------------------------------
# Result mappers
# ---------------------------------------------------------------------------


def _placeholder_metadata() -> EvaluationMetadata:
    """Minimal metadata placeholder for result comparison objects.

    Only ``answer`` and ``explanation`` are compared in contract assertions;
    metadata contains non-deterministic fields (timing, evaluation ID, etc.)
    and is intentionally excluded.
    """
    return EvaluationMetadata(
        evaluator_metadata=EvaluatorMetadata(
            id="vocabulary",
            version="0.1",
            name="Vocabulary",
            description="Contract test placeholder.",
            maturity=EvaluatorMaturity.alpha,
        ),
        evaluation_settings=None,  # type: ignore[arg-type]
        input_metadata={},
        status=Status.succeeded,
    )


def vocabulary_grade34_notebook_to_sdk_result(
    case: ContractCase,
) -> TextComplexityResult:
    """Convert a grades 3–4 ``expected_result`` dict to a ``TextComplexityResult``.

    The notebook outputs a plain dict from ``JsonOutputParser``; the SDK wraps
    that into ``TextComplexityResult``.  This function performs the same mapping
    so tests can assert equality.

    Only ``answer`` and ``explanation`` are compared — ``metadata`` is a
    placeholder because it contains non-deterministic fields.

    Args:
        case: A loaded :class:`~loader.ContractCase` with a populated
            ``expected_result`` (grades 3–4 format).

    Returns:
        A ``TextComplexityResult`` built from the contract's expected output.
    """
    r = case.expected_result
    # Normalise the score string: the notebook may return "very complex" (spaces).
    raw_score = r["complexity_score"].lower().replace(" ", "_")
    answer = TextComplexityAnswer.from_score(raw_score)
    explanation = EvaluationExplanation(
        summary=r["reasoning"],
        details={
            "tier_2_words": r["tier_2_words"],
            "tier_3_words": r["tier_3_words"],
            "archaic_words": r["archaic_words"],
            "other_complex_words": r["other_complex_words"],
        },
    )
    return TextComplexityResult(
        answer=answer,
        explanation=explanation,
        metadata=_placeholder_metadata(),
    )


def vocabulary_other_grades_notebook_to_sdk_result(
    case: ContractCase,
) -> TextComplexityResult:
    """Convert a grades 5–12 ``expected_result`` dict to a ``TextComplexityResult``.

    The OTHER_GRADES path uses the same Output-style schema as grades 3–4, so
    ``expected_result`` contains a string ``complexity_score`` (e.g. "slightly
    complex") which is normalised to underscore form before mapping, plus the
    same word-list fields as the notebook dict.

    Only ``answer`` and ``explanation`` are compared — ``metadata`` is a
    placeholder because it contains non-deterministic fields.

    Args:
        case: A loaded :class:`~loader.ContractCase` with a populated
            ``expected_result`` (grades 5–12 format).

    Returns:
        A ``TextComplexityResult`` built from the contract's expected output.
    """
    r = case.expected_result
    score = r["complexity_score"].lower().replace(" ", "_")
    answer = TextComplexityAnswer.from_score(score)
    explanation = EvaluationExplanation(
        summary=r["reasoning"],
        details={
            "tier_2_words": r["tier_2_words"],
            "tier_3_words": r["tier_3_words"],
            "archaic_words": r["archaic_words"],
            "other_complex_words": r["other_complex_words"],
        },
    )
    return TextComplexityResult(
        answer=answer,
        explanation=explanation,
        metadata=_placeholder_metadata(),
    )
