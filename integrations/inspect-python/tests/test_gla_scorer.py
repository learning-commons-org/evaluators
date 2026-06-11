"""Tests for the GLA Inspect scorer wrapper."""

from __future__ import annotations

import math
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from inspect_ai.scorer import CORRECT, INCORRECT

from learning_commons_evaluators.schemas.errors import APIError, ConfigurationError
from learning_commons_inspect_scorers.gla import _acceptable_bands, gla_scorer

GRADE_BANDS = ["K-1", "2-3", "4-5", "6-8", "9-10", "11-CCR"]


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_state(completion: str = "", metadata: dict | None = None) -> MagicMock:
    state = MagicMock()
    state.output.completion = completion
    state.metadata = metadata or {}
    return state


def _make_target() -> MagicMock:
    return MagicMock()


def _make_gla_result(grade: str = "6-8") -> MagicMock:
    result = MagicMock()
    result.answer.score = grade
    result.explanation.summary = "Test reasoning."
    result.explanation.details = {
        "alternative_grade": "4-5",
        "scaffolding_needed": "Pre-teach vocabulary.",
    }
    return result


def _make_scorer(grade_result: str = "6-8", side_effect=None, **scorer_kwargs):
    """Build a gla_scorer with a patched evaluator.

    Patches GradeLevelAppropriatenessEvaluator so no real LLM calls are made.
    The evaluator instance captured in the scorer closure is the mock, so calls
    work normally after construction.
    """
    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = AsyncMock(
        return_value=_make_gla_result(grade_result),
        side_effect=side_effect,
    )
    with patch(
        "learning_commons_inspect_scorers.gla.GradeLevelAppropriatenessEvaluator",
        return_value=mock_evaluator,
    ):
        scorer_fn = gla_scorer(**scorer_kwargs)
    # The scorer closure already holds the mock_evaluator instance — no further
    # patching needed for subsequent calls.
    return scorer_fn, mock_evaluator


# ── _acceptable_bands ────────────────────────────────────────────────────────


class TestAcceptableBands:
    def test_middle_grade_allow_adjacent(self):
        assert _acceptable_bands("6-8", allow_adjacent=True) == {"4-5", "6-8", "9-10"}

    def test_lower_boundary_allow_adjacent(self):
        # K-1 is at index 0 — no band below it
        assert _acceptable_bands("K-1", allow_adjacent=True) == {"K-1", "2-3"}

    def test_upper_boundary_allow_adjacent(self):
        # 11-CCR is at end — no band above it
        assert _acceptable_bands("11-CCR", allow_adjacent=True) == {"9-10", "11-CCR"}

    def test_exact_match_only(self):
        assert _acceptable_bands("6-8", allow_adjacent=False) == {"6-8"}

    def test_invalid_grade_returns_singleton(self):
        assert _acceptable_bands("invalid", allow_adjacent=True) == {"invalid"}

    @pytest.mark.parametrize("band", GRADE_BANDS)
    def test_all_bands_are_valid(self, band):
        result = _acceptable_bands(band, allow_adjacent=True)
        assert band in result
        assert len(result) >= 1


# ── gla_scorer — factory validation ──────────────────────────────────────────


class TestGlaScorerFactory:
    def test_invalid_text_source_raises(self):
        with pytest.raises(ValueError, match="text_source must be"):
            gla_scorer(text_source="html")

    def test_valid_text_sources_accepted(self):
        for src in ("completion", "artifacts"):
            with patch("learning_commons_inspect_scorers.gla.GradeLevelAppropriatenessEvaluator"):
                gla_scorer(text_source=src)  # must not raise


# ── gla_scorer — score routing ────────────────────────────────────────────────


class TestGlaScorer:
    async def test_matching_grade_returns_correct(self):
        scorer_fn, _ = _make_scorer(grade_result="6-8")
        state = _make_state(completion="Sample text.", metadata={"target_grade": "6-8"})
        score = await scorer_fn(state, _make_target())
        assert score.value == CORRECT
        assert score.answer == "6-8"

    async def test_adjacent_grade_passes_when_allow_adjacent(self):
        scorer_fn, _ = _make_scorer(grade_result="4-5")
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        assert (await scorer_fn(state, _make_target())).value == CORRECT

    async def test_non_adjacent_grade_fails(self):
        scorer_fn, _ = _make_scorer(grade_result="K-1")
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        assert (await scorer_fn(state, _make_target())).value == INCORRECT

    async def test_exact_match_only_when_adjacent_disabled(self):
        scorer_fn, _ = _make_scorer(grade_result="4-5", allow_adjacent=False)
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        assert (await scorer_fn(state, _make_target())).value == INCORRECT

    async def test_boundary_k1_adjacent_passes(self):
        scorer_fn, _ = _make_scorer(grade_result="2-3")
        state = _make_state(completion="Sample.", metadata={"target_grade": "K-1"})
        assert (await scorer_fn(state, _make_target())).value == CORRECT

    async def test_boundary_11ccr_adjacent_passes(self):
        scorer_fn, _ = _make_scorer(grade_result="9-10")
        state = _make_state(completion="Sample.", metadata={"target_grade": "11-CCR"})
        assert (await scorer_fn(state, _make_target())).value == CORRECT

    async def test_missing_target_grade_returns_unscored(self):
        scorer_fn, _ = _make_scorer()
        state = _make_state(completion="Sample.", metadata={})
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))

    async def test_invalid_target_grade_returns_unscored(self):
        scorer_fn, _ = _make_scorer()
        state = _make_state(completion="Sample.", metadata={"target_grade": "Grade 5"})
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))

    async def test_empty_completion_returns_unscored(self):
        scorer_fn, mock_evaluator = _make_scorer()
        state = _make_state(completion="", metadata={"target_grade": "6-8"})
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))
        mock_evaluator.evaluate.assert_not_called()

    async def test_api_error_returns_unscored(self):
        scorer_fn, _ = _make_scorer(side_effect=APIError("rate limit"))
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))
        assert "rate limit" in score.explanation

    async def test_configuration_error_propagates(self):
        scorer_fn, _ = _make_scorer(side_effect=ConfigurationError("no key"))
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        with pytest.raises(ConfigurationError):
            await scorer_fn(state, _make_target())

    async def test_score_metadata_populated(self):
        scorer_fn, _ = _make_scorer(grade_result="6-8")
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        score = await scorer_fn(state, _make_target())
        assert score.metadata["gla_grade"] == "6-8"
        assert score.metadata["target_grade"] == "6-8"
        assert score.metadata["alternative_grade"] == "4-5"
        assert score.metadata["scaffolding_needed"] == "Pre-teach vocabulary."

    async def test_custom_target_grade_key(self):
        scorer_fn, _ = _make_scorer(grade_result="6-8", target_grade_key="expected_grade")
        state = _make_state(completion="Sample.", metadata={"expected_grade": "6-8"})
        assert (await scorer_fn(state, _make_target())).value == CORRECT

    async def test_custom_target_grade_key_absent_returns_unscored(self):
        scorer_fn, _ = _make_scorer(target_grade_key="expected_grade")
        state = _make_state(completion="Sample.", metadata={"target_grade": "6-8"})
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))

    async def test_custom_grader_model_passed_to_adapter(self):
        with patch(
            "learning_commons_inspect_scorers.gla.InspectModelAdapter"
        ) as mock_adapter_cls, patch(
            "learning_commons_inspect_scorers.gla.GradeLevelAppropriatenessEvaluator"
        ):
            gla_scorer(grader_model="openai/gpt-4o")
        mock_adapter_cls.assert_called_once_with("openai/gpt-4o")


# ── gla_scorer — artifacts text source ────────────────────────────────────────


class TestGlaScorerArtifacts:
    async def test_reads_artifact_files(self, tmp_path: Path):
        artifact = tmp_path / "lesson.md"
        artifact.write_text("The mitochondria is the powerhouse of the cell.")

        scorer_fn, mock_evaluator = _make_scorer(
            grade_result="6-8", text_source="artifacts"
        )
        state = _make_state(
            metadata={
                "target_grade": "6-8",
                "artifacts": [{"path": str(artifact), "filename": "lesson.md"}],
            }
        )
        score = await scorer_fn(state, _make_target())
        assert score.value == CORRECT
        called_text = mock_evaluator.evaluate.call_args[0][0].text.value
        assert "mitochondria" in called_text

    async def test_unreadable_artifact_returns_unscored(self):
        scorer_fn, mock_evaluator = _make_scorer(text_source="artifacts")
        state = _make_state(
            metadata={
                "target_grade": "6-8",
                "artifacts": [{"path": "/nonexistent/path.md", "filename": "missing.md"}],
            }
        )
        score = await scorer_fn(state, _make_target())
        assert math.isnan(float(score.value))
        mock_evaluator.evaluate.assert_not_called()

    async def test_multiple_artifacts_joined_with_separator(self, tmp_path: Path):
        f1 = tmp_path / "a.md"
        f2 = tmp_path / "b.md"
        f1.write_text("First document.")
        f2.write_text("Second document.")

        scorer_fn, mock_evaluator = _make_scorer(
            grade_result="4-5", text_source="artifacts"
        )
        state = _make_state(
            metadata={
                "target_grade": "4-5",
                "artifacts": [
                    {"path": str(f1), "filename": "a.md"},
                    {"path": str(f2), "filename": "b.md"},
                ],
            }
        )
        await scorer_fn(state, _make_target())
        called_text = mock_evaluator.evaluate.call_args[0][0].text.value
        assert "First document." in called_text
        assert "Second document." in called_text
        assert "---" in called_text


# ── Integration tests (mockllm/model) ────────────────────────────────────────


class TestGlaScorerIntegration:
    """End-to-end tests using Inspect's built-in mockllm/model provider.

    These tests validate that gla_scorer satisfies the Inspect Scorer protocol
    and wires correctly through eval() — without making any real LLM calls.
    The GLA evaluator itself is still mocked at the SDK boundary.

    .. note::
        These tests are synchronous (``def``, not ``async def``) because
        ``inspect_ai.eval()`` calls ``anyio.run()`` internally to start its own
        event loop. Using ``async def`` under ``pytest-asyncio asyncio_mode=auto``
        would start a second event loop, causing an anyio ``ScopeMismatch`` error.
    """

    def test_scorer_wires_through_eval(self):
        from unittest.mock import AsyncMock, patch

        from inspect_ai import Task, eval
        from inspect_ai.dataset import Sample
        from inspect_ai.solver import generate

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=_make_gla_result("6-8"))

        with patch(
            "learning_commons_inspect_scorers.gla.GradeLevelAppropriatenessEvaluator",
            return_value=mock_evaluator,
        ):
            scorer = gla_scorer()

        task = Task(
            dataset=[
                Sample(
                    input="Write a short paragraph for 6th graders.",
                    metadata={"target_grade": "6-8"},
                )
            ],
            solver=[generate()],
            scorer=scorer,
        )

        log = eval(task, model="mockllm/model")[0]

        assert log.status == "success"
        sample = log.samples[0]
        assert sample.score is not None
        assert sample.score.value == CORRECT

    def test_unscored_sample_does_not_count_as_failure(self):
        from unittest.mock import AsyncMock, patch

        from inspect_ai import Task, eval
        from inspect_ai.dataset import Sample
        from inspect_ai.solver import generate

        mock_evaluator = MagicMock()
        mock_evaluator.evaluate = AsyncMock(return_value=_make_gla_result("6-8"))

        with patch(
            "learning_commons_inspect_scorers.gla.GradeLevelAppropriatenessEvaluator",
            return_value=mock_evaluator,
        ):
            scorer = gla_scorer()

        # Sample has no target_grade — should be unscored, not INCORRECT
        task = Task(
            dataset=[Sample(input="Write something.", metadata={})],
            solver=[generate()],
            scorer=scorer,
        )

        log = eval(task, model="mockllm/model")[0]
        sample = log.samples[0]
        assert sample.score is not None
        assert math.isnan(float(sample.score.value))
