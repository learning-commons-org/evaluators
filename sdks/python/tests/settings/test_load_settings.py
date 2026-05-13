"""Tests for :mod:`learning_commons_evaluators.settings.load_settings`."""

from __future__ import annotations

import importlib.resources
import textwrap
from pathlib import Path

import pytest

from learning_commons_evaluators.schemas.config import (
    EvaluationSettings,
    LlmProvider,
    PromptSettings,
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
            maturity = "GA"

            [[evaluator_metadata.inputs]]
            name = "text"
            type = "TextInputField"

            [evaluation_settings]
            marker = 7
            """
        ).strip()
    )
    result = load_evaluator_settings(path, _MiniSettings)
    assert result.evaluator_metadata.maturity == EvaluatorMaturity.ga
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
            maturity = "ga"

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
            maturity = "ga"
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
            maturity = "ga"

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
            maturity = "ga"

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
    assert result.evaluation_settings.prompt_settings_main.provider_type == LlmProvider.GOOGLE
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
            maturity = "ga"

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
    path = tmp_path / "bad_prompt.toml"
    path.write_text(
        textwrap.dedent(
            """
            [evaluator_metadata]
            id = "e"
            version = "1.0"
            name = "N"
            description = "D"
            maturity = "ga"

            [evaluation_settings]
            marker = 0

            [evaluation_settings.prompt_settings_main]
            provider_type = "google"
            model = "m"
            """
        ).strip()
    )
    with pytest.raises(
        ConfigurationError, match="Invalid \\[evaluation_settings.prompt_settings_main\\]"
    ):
        load_evaluator_settings(path, _WithPromptSettings)
