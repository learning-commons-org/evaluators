"""Inspect scorer wrapper for the Grade Level Appropriateness evaluator."""

from __future__ import annotations

from pathlib import Path

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
    OutputValidationError,
)
from learning_commons_evaluators.schemas.grade_level_appropriateness import GradeLevelAnswer

from learning_commons_inspect_scorers.adapter import InspectModelAdapter

GRADE_BANDS = [m.score for m in GradeLevelAnswer]
MAX_ARTIFACT_CHARS = 20_000
MAX_TOTAL_ARTIFACT_CHARS = 90_000  # safely under the GLA evaluator's 100k limit


def _completion_text(state: TaskState) -> str:
    return (state.output.completion or "")[:MAX_ARTIFACT_CHARS]


def _artifact_text(state: TaskState) -> str:
    artifacts = state.metadata.get("artifacts", [])
    parts = []
    for a in artifacts:
        path_str = a.get("path", "")
        filename = a.get("filename", "unknown")
        try:
            content = Path(path_str).read_text(encoding="utf-8")[:MAX_ARTIFACT_CHARS]
            parts.append(f"### {filename}\n\n{content}")
        except Exception:
            # Skip unreadable artifacts rather than feeding error strings to the LLM.
            pass
    joined = "\n\n---\n\n".join(parts) if parts else ""
    return joined[:MAX_TOTAL_ARTIFACT_CHARS]


def _acceptable_bands(target: str, allow_adjacent: bool) -> set[str]:
    idx = GRADE_BANDS.index(target) if target in GRADE_BANDS else -1
    if idx == -1 or not allow_adjacent:
        return {target}
    return {GRADE_BANDS[i] for i in range(max(0, idx - 1), min(len(GRADE_BANDS), idx + 2))}


@scorer(metrics=[accuracy()])
def gla_scorer(
    grader_model: str = "anthropic/claude-opus-4-8",
    text_source: str = "completion",
    target_grade_key: str = "target_grade",
    allow_adjacent: bool = True,
):
    """Score output for grade-level appropriateness against a target grade band.

    Uses Inspect's active model (via InspectModelAdapter) to run the GLA evaluator.
    No separate LLM API keys are required — the model is resolved through Inspect's
    own model configuration.

    Args:
        grader_model: Inspect model string for the grading LLM.
                      Default: ``"anthropic/claude-opus-4-8"``.
        text_source: Where to read the text to evaluate. Must be ``"completion"``
                     (default, uses ``state.output.completion``) or ``"artifacts"``
                     (concatenates ``state.metadata["artifacts"]`` file contents).
        target_grade_key: Metadata key holding the expected grade band string.
                          Default: ``"target_grade"``. Must be one of: K-1, 2-3,
                          4-5, 6-8, 9-10, 11-CCR.
        allow_adjacent: If ``True`` (default), the one grade band above or below
                        the target also counts as a pass. Set to ``False`` for an
                        exact match.

    Returns ``Score.unscored()`` when ``target_grade_key`` is absent or not a valid
    grade band, when no text is available to evaluate, or when a transient API/parse
    error occurs. Re-raises ``ConfigurationError`` and ``InputValidationError`` as
    task-level failures.

    ``Score.value`` is ``CORRECT`` (pass) or ``INCORRECT`` (fail).
    ``Score.metadata`` contains ``gla_grade``, ``target_grade``, ``alternative_grade``,
    and ``scaffolding_needed``.
    """
    if text_source not in ("completion", "artifacts"):
        raise ValueError(f"text_source must be 'completion' or 'artifacts', got {text_source!r}")

    adapter = InspectModelAdapter(grader_model)
    # config is required by BaseEvaluator but no API keys are read here —
    # the llm_provider bypasses the LangChain provider path entirely.
    config = create_config_no_telemetry()
    evaluator = GradeLevelAppropriatenessEvaluator(config=config, llm_provider=adapter)
    get_text = _artifact_text if text_source == "artifacts" else _completion_text

    async def score(state: TaskState, target: Target) -> Score | None:
        target_grade: str = (state.metadata.get(target_grade_key) or "").strip()
        if not target_grade or target_grade not in GRADE_BANDS:
            return Score.unscored(
                explanation=(
                    f"{target_grade_key!r} is missing or not a valid grade band. "
                    f"Valid bands: {', '.join(GRADE_BANDS)}"
                ),
                metadata={"target_grade_key": target_grade_key, "target_grade": target_grade or None},
            )

        text = get_text(state)
        if not text.strip():
            return Score.unscored(
                explanation="No text to evaluate (empty completion or no readable artifacts).",
                metadata={"target_grade": target_grade, "gla_grade": None},
            )

        try:
            result = await evaluator.evaluate(
                GradeLevelAppropriatenessEvaluationInput(text=text)
            )
        except (ConfigurationError, InputValidationError):
            raise  # setup/programming errors — let Inspect surface them as task failures
        except APIError as exc:  # OutputValidationError is a subclass of APIError
            return Score.unscored(
                explanation=f"GLA evaluation failed: {exc}",
                metadata={"target_grade": target_grade, "gla_grade": None},
            )

        gla_grade: str = result.answer.score  # e.g. "6-8"
        passed = gla_grade in _acceptable_bands(target_grade, allow_adjacent)

        return Score(
            value=CORRECT if passed else INCORRECT,
            answer=gla_grade,
            explanation=(
                f"Target: {target_grade} | GLA: {gla_grade} | "
                f"{'PASS' if passed else 'FAIL'}\n"
                + (result.explanation.summary or "")
            ),
            metadata={
                "gla_grade": gla_grade,
                "target_grade": target_grade,
                "alternative_grade": result.explanation.details["alternative_grade"],
                "scaffolding_needed": result.explanation.details["scaffolding_needed"],
            },
        )

    return score
