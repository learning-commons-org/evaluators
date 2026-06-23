"""Inspect scorer wrapper for the Grade Level Appropriateness evaluator."""

from __future__ import annotations

from collections.abc import Callable

from inspect_ai.scorer import CORRECT, INCORRECT, Score, Target, accuracy, scorer
from inspect_ai.solver import TaskState
from learning_commons_evaluators.config import create_config_no_telemetry
from learning_commons_evaluators.evaluators.grade_level_appropriateness import (
    GradeLevelAppropriatenessEvaluationInput,
    GradeLevelAppropriatenessEvaluator,
)
from learning_commons_evaluators.schemas.errors import (
    APIError,
    ConfigurationError,
    InputValidationError,
)
from learning_commons_evaluators.schemas.grade_level_appropriateness import GradeLevelAnswer

from learning_commons_inspect_scorers.adapter import InspectModelAdapter

GRADE_BANDS = [m.score for m in GradeLevelAnswer]


def _completion_text(state: TaskState) -> str | None:
    return state.output.completion or None


def _acceptable_bands(target: str, allow_adjacent: bool) -> set[str]:
    idx = GRADE_BANDS.index(target) if target in GRADE_BANDS else -1
    if idx == -1 or not allow_adjacent:
        return {target}
    return {GRADE_BANDS[i] for i in range(max(0, idx - 1), min(len(GRADE_BANDS), idx + 2))}


@scorer(metrics=[accuracy()])
def gla_scorer(
    grader_model: str = "anthropic/claude-opus-4-8",
    target_grade_key: str = "target_grade",
    allow_adjacent: bool = True,
    text_fn: Callable[[TaskState], str | None] | None = None,
):
    """Score output for grade-level appropriateness against a target grade band.

    Uses Inspect's active model (via InspectModelAdapter) to run the GLA evaluator.
    No separate LLM API keys are required — the model is resolved through Inspect's
    own model configuration.

    Args:
        grader_model: Inspect model string for the grading LLM.
                      Default: ``"anthropic/claude-opus-4-8"``.
        target_grade_key: Metadata key holding the expected grade band string.
                          Default: ``"target_grade"``. Must be one of: K-1, 2-3,
                          4-5, 6-8, 9-10, 11-CCR.
        allow_adjacent: If ``True`` (default), the one grade band above or below
                        the target also counts as a pass. Set to ``False`` for an
                        exact match.
        text_fn: Returns the text to grade for a sample, given the ``TaskState``.
                 Defaults to ``state.output.completion``. Supply a custom function
                 to source text elsewhere — e.g. files your task produced — keeping
                 any task-specific knowledge (file layout, naming, formatting) out
                 of this package. Return ``None`` or empty to skip the sample. The
                 caller is responsible for keeping the text within the GLA
                 evaluator's input-length limit; oversized text raises
                 ``InputValidationError`` as a task failure.

    Returns ``None`` (skip — the sample is omitted from this scorer's results) when
    ``target_grade_key`` is absent or not a valid grade band, when ``text_fn``
    yields no text, or when a transient API/parse error occurs. Re-raises
    ``ConfigurationError`` and ``InputValidationError`` as task-level failures.

    ``Score.value`` is ``CORRECT`` (pass) or ``INCORRECT`` (fail).
    ``Score.metadata`` contains ``gla_grade``, ``target_grade``, ``alternative_grade``,
    and ``scaffolding_needed``.
    """
    adapter = InspectModelAdapter(grader_model)
    # config is required by BaseEvaluator but no API keys are read here —
    # the llm_provider bypasses the LangChain provider path entirely.
    config = create_config_no_telemetry()
    evaluator = GradeLevelAppropriatenessEvaluator(config=config, llm_provider=adapter)
    get_text = text_fn or _completion_text

    async def score(state: TaskState, target: Target) -> Score | None:
        # Skip paths return None (not Score.unscored()): None omits the sample from
        # this scorer's results entirely, which every Inspect metric — and custom
        # report renderers — handle cleanly. Score.unscored() records a NaN value
        # that naive renderers can mistake for a real score and average into the mean.
        target_grade: str = (state.metadata.get(target_grade_key) or "").strip()
        if not target_grade or target_grade not in GRADE_BANDS:
            return None

        text = get_text(state)
        if not text or not text.strip():
            return None

        try:
            result = await evaluator.evaluate(GradeLevelAppropriatenessEvaluationInput(text=text))
        except (ConfigurationError, InputValidationError):
            raise  # setup/programming errors — let Inspect surface them as task failures
        except APIError:  # OutputValidationError is a subclass; transient grading failure → skip
            return None

        gla_grade: str = result.answer.score
        passed = gla_grade in _acceptable_bands(target_grade, allow_adjacent)

        return Score(
            value=CORRECT if passed else INCORRECT,
            answer=gla_grade,
            explanation=(
                f"Target: {target_grade} | GLA: {gla_grade} | "
                f"{'PASS' if passed else 'FAIL'}\n" + (result.explanation.summary or "")
            ),
            metadata={
                "gla_grade": gla_grade,
                "target_grade": target_grade,
                "alternative_grade": result.explanation.details["alternative_grade"],
                "scaffolding_needed": result.explanation.details["scaffolding_needed"],
            },
        )

    return score
