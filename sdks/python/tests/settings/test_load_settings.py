"""Tests for :mod:`learning_commons_evaluators.settings.load_settings`."""

from __future__ import annotations

import importlib.resources
import os
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    LLMProvider,
    PromptSettings,
)
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
)
from learning_commons_evaluators.schemas.errors import ConfigurationError
from learning_commons_evaluators.schemas.input_specs import TextInputSpec
from learning_commons_evaluators.schemas.metadata import EvaluatorMaturity
from learning_commons_evaluators.settings.load_settings import (
    load_evaluator_settings,
    load_settings,
    shared_settings_root,
)


class _MiniSettings(EvaluationSettings):
    """Minimal evaluation_settings block for loader tests."""

    marker: int = 0


class _WithPromptSettings(EvaluationSettings):
    marker: int = 0
    prompt_settings_main: PromptSettings


def test_load_evaluator_settings_end_to_end(tmp_path: Path) -> None:
    path = tmp_path / "eval.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "EARLY_ACCESS"

            [[evaluator_metadata.inputs]]
            name = "text"
            type = "TextInputField"

            [evaluation_settings]
            marker = 7
            """
        ).strip()
    )
    result = load_evaluator_settings(path, _MiniSettings)
    assert result.evaluator_metadata.maturity == EvaluatorMaturity.early_access
    assert isinstance(result.evaluator_metadata.inputs["text"], TextInputSpec)
    assert result.evaluation_settings.marker == 7


def test_load_evaluator_settings_wraps_metadata_validation(tmp_path: Path) -> None:
    path = tmp_path / "bad.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = ""
            version = "1"
            name = "N"
            description = "D"
            maturity = "early_access"

            [evaluation_settings]
            marker = 0
            """
        ).strip()
    )
    with pytest.raises(ConfigurationError, match="Invalid \\[evaluator_metadata\\]"):
        load_evaluator_settings(path, _MiniSettings)


def test_load_settings_path_and_str_same_result(tmp_path: Path) -> None:
    path = tmp_path / "raw.toml"
    path.write_text('mode = "test"\n')
    by_path = load_settings(path)
    by_str = load_settings(str(path))
    assert by_path == by_str == {"mode": "test"}


def test_load_settings_traversable_package_file() -> None:
    root = importlib.resources.files("tests.settings.fixtures")
    tom = root.joinpath("minimal.toml")
    assert load_settings(tom) == {"answer": 42}


def test_shared_settings_root_env_overrides(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    custom = tmp_path / "custom_settings"
    custom.mkdir()
    monkeypatch.setenv("EVALUATORS_SETTINGS_DIR", str(custom))
    assert shared_settings_root() == custom


def test_shared_settings_root_bundled_points_at_package(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("EVALUATORS_SETTINGS_DIR", raising=False)
    root = shared_settings_root()
    assert root.joinpath("load_settings.py").is_file()


def test_load_evaluator_settings_missing_evaluator_metadata(tmp_path: Path) -> None:
    path = tmp_path / "no_meta.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluation_settings]
            marker = 0
            """
        ).strip()
    )
    with pytest.raises(
        ConfigurationError, match="Missing required section \\[evaluator_metadata\\]"
    ):
        load_evaluator_settings(path, _MiniSettings)


def test_load_evaluator_settings_missing_evaluation_settings(tmp_path: Path) -> None:
    path = tmp_path / "no_eval.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "early_access"
            """
        ).strip()
    )
    with pytest.raises(
        ConfigurationError, match="Missing required section \\[evaluation_settings\\]"
    ):
        load_evaluator_settings(path, _MiniSettings)


def test_load_evaluator_settings_invalid_evaluation_settings(tmp_path: Path) -> None:
    path = tmp_path / "bad_eval.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "early_access"

            [evaluation_settings]
            marker = "not-int"
            """
        ).strip()
    )
    with pytest.raises(ConfigurationError, match="Invalid \\[evaluation_settings\\]"):
        load_evaluator_settings(path, _MiniSettings)


def test_load_evaluator_settings_prompt_settings_and_prompts(tmp_path: Path) -> None:
    path = tmp_path / "prompts.toml"
    path.write_text(
        textwrap.dedent(
            r'''
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "early_access"

            [evaluation_settings]
            marker = 1

            [evaluation_settings.prompt_settings_main]
            provider_type = "GOOGLE"
            model = "gemini-2.0-flash"
            temperature = 0.25

            [prompts]
            system_prompt = """hello
               \nworld"""
            '''
        ).strip()
    )
    result = load_evaluator_settings(path, _WithPromptSettings)
    assert result.evaluation_settings.prompt_settings_main.provider_type == LLMProvider.GOOGLE
    assert result.evaluation_settings.prompt_settings_main.model == "gemini-2.0-flash"
    assert result.evaluation_settings.prompt_settings_main.temperature == 0.25
    assert result.prompts["system_prompt"] == "hello\n\nworld"


def test_load_evaluator_settings_rejects_non_string_prompt_value(tmp_path: Path) -> None:
    path = tmp_path / "bad_prompt_type.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "early_access"

            [evaluation_settings]
            marker = 0

            [prompts]
            n = 3
            """
        ).strip()
    )
    with pytest.raises(ConfigurationError, match="Invalid \\[prompts\\].n"):
        load_evaluator_settings(path, _MiniSettings)


def test_load_evaluator_settings_invalid_prompt_settings_block(tmp_path: Path) -> None:
    """Unknown ``[[evaluator_metadata.inputs]].type`` must raise a clear configuration error."""
    path = tmp_path / "bad_prompt.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "x"
            version = "0.1"
            name = "X"
            description = "X"
            maturity = "early_access"

            [[evaluator_metadata.inputs]]
            name = "mystery"
            type = "UnknownInputField"

            [evaluation_settings.prompt_settings_step_conventionality_evaluation]
            provider_type = "GOOGLE"
            model = "gemini-2.0-flash"
            temperature = 0
            """
        ).strip()
    )
    with pytest.raises(ConfigurationError, match="UnknownInputField"):
        load_evaluator_settings(path, ConventionalityEvaluationSettings)


# ---------------------------------------------------------------------------
# shared_settings_root
# ---------------------------------------------------------------------------


class TestSharedSettingsRoot:
    def test_env_var_overrides_bundled_path(self, tmp_path: Path) -> None:
        with patch.dict(os.environ, {"EVALUATORS_SETTINGS_DIR": str(tmp_path)}):
            assert shared_settings_root() == tmp_path

    def test_importlib_fallback_resolves_to_existing_directory(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "EVALUATORS_SETTINGS_DIR"}
        with patch.dict(os.environ, env, clear=True):
            root = shared_settings_root()
        assert root.is_dir(), f"shared_settings_root() resolved to non-directory: {root}"

    def test_bundled_contract_tests_are_present(self) -> None:
        """The bundled package must contain contracts.toml for each evaluator.

        The evaluator settings TOML is intentionally NOT bundled (evaluators use _generated_*_settings.py).
        contracts.toml IS bundled so contract tests work against an installed package.
        """
        env = {k: v for k, v in os.environ.items() if k != "EVALUATORS_SETTINGS_DIR"}
        with patch.dict(os.environ, env, clear=True):
            root = shared_settings_root()
        for evaluator in ("conventionality",):
            assert (root / evaluator / "contracts.toml").is_file(), (
                f"Bundled {evaluator}/contracts.toml not found — "
                f"run 'python scripts/generate_settings.py --sync'"
            )


# ---------------------------------------------------------------------------
# Settings bundle sync guard
# ---------------------------------------------------------------------------
#
# What is and isn't bundled in the package:
#
#   BUNDLED:   contracts.toml — needed so contract tests run against an
#              installed package without access to sdks/settings/.
#
#   NOT BUNDLED: settings.toml — not needed at runtime; evaluators import
#              from _generated_*_settings.py (pre-built at generation time).
#              The canonical copy lives in sdks/settings/ and is the input to
#              `make generate-settings`.
#
# If a sync test fails, run from the repo root:
#   python scripts/generate_settings.py --sync    — copies contracts.toml canonical → bundled
#   python scripts/generate_settings.py --check   — verifies generated .py files are up to date


def _bundled_settings_root() -> Path:
    """Return the importlib.resources path for bundled settings, bypassing EVALUATORS_SETTINGS_DIR."""
    pkg = importlib.resources.files("learning_commons_evaluators.settings")
    return Path(str(pkg))


def _canonical_settings_root() -> Path | None:
    """Return sdks/settings/ relative to this file, or None if not in the monorepo."""
    # This file lives at: sdks/python/tests/settings/test_load_settings.py
    # parents[3] = sdks/
    candidate = Path(__file__).parents[3] / "settings"
    return candidate if candidate.is_dir() else None


@pytest.mark.parametrize("evaluator", ["conventionality", "vocabulary"])
def test_bundled_contract_tests_match_canonical(evaluator: str) -> None:
    """Bundled contracts.toml must be byte-for-byte identical to sdks/settings/.

    Skipped when running outside the monorepo (e.g., from an installed package).
    If this fails, run ``python scripts/generate_settings.py --sync`` from the repo root.
    """
    canonical_root = _canonical_settings_root()
    if canonical_root is None:
        pytest.skip("sdks/settings/ not found — running outside the monorepo")

    canonical = canonical_root / evaluator / "contracts.toml"
    if not canonical.exists():
        pytest.skip(f"Canonical file not found: {canonical}")

    bundled = _bundled_settings_root() / evaluator / "contracts.toml"
    assert bundled.exists(), (
        f"Bundled {evaluator}/contracts.toml not found.\n"
        f"Run: python scripts/generate_settings.py --sync"
    )
    assert canonical.read_bytes() == bundled.read_bytes(), (
        f"{evaluator}/contracts.toml is out of sync.\n"
        f"  canonical: {canonical}\n"
        f"  bundled:   {bundled}\n"
        f"Fix: python scripts/generate_settings.py --sync"
    )
