"""Tests for load_settings.

Covers: load_settings(), _require(), _parse_prompts() (including prompt whitespace
normalization), load_evaluator_settings(),
and shared_settings_root() — including every conditional branch in each function.
Also contains the settings-sync guard: a test that fails if the bundled package
copies of settings diverge from the canonical sdks/settings/ source of truth.
"""

import importlib.resources
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from learning_commons_evaluators.errors import ConfigurationError
from learning_commons_evaluators.schemas.conventionality import (
    ConventionalityEvaluationSettings,
)
from learning_commons_evaluators.schemas.metadata import EvaluatorMaturity
from learning_commons_evaluators.settings.load_settings import (
    EvaluatorSettingsResult,
    _parse_prompts,
    _require,
    load_evaluator_settings,
    load_settings,
    shared_settings_root,
)

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _write_toml(tmp_path: Path, content: str) -> Path:
    """Write TOML content to evaluator.toml inside tmp_path and return the path."""
    path = tmp_path / "evaluator.toml"
    path.write_text(content, encoding="utf-8")
    return path


# Minimal [evaluator_metadata] section reused across several tests.
_MINIMAL_META = """\
[evaluator_metadata]
id = "x"
version = "0.1"
name = "X"
description = "X"
maturity = "beta"
"""

# Minimal [evaluation_settings] section reused across several tests.
_MINIMAL_EVAL_SETTINGS = """\
[evaluation_settings.prompt_settings_step_main]
type = "GOOGLE"
model = "gemini-2.0-flash"
temperature = 0
"""


# ---------------------------------------------------------------------------
# load_settings (raw TOML loader)
# ---------------------------------------------------------------------------


class TestLoadSettings:
    def test_parses_nested_sections(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[section]
key = "value"
n = 42
[section.nested]
foo = "bar"
""",
        )
        data = load_settings(path)
        assert data["section"]["key"] == "value"
        assert data["section"]["n"] == 42
        assert data["section"]["nested"]["foo"] == "bar"

    def test_accepts_str_path(self, tmp_path: Path) -> None:
        path = _write_toml(tmp_path, 'title = "hello"')
        assert load_settings(str(path))["title"] == "hello"

    def test_raises_file_not_found(self) -> None:
        with pytest.raises(FileNotFoundError):
            load_settings(Path("/nonexistent/path/settings.toml"))


# ---------------------------------------------------------------------------
# _require
# ---------------------------------------------------------------------------


class TestRequire:
    def test_raises_when_value_is_none(self) -> None:
        with pytest.raises(ConfigurationError, match="missing_field"):
            _require("missing_field", None, "section")

    def test_raises_when_value_is_blank_string(self) -> None:
        with pytest.raises(ConfigurationError, match="blank_field"):
            _require("blank_field", "   ", "section")

    def test_passes_for_non_empty_string(self) -> None:
        _require("key", "value", "section")  # must not raise

    def test_passes_for_numeric_value(self) -> None:
        """An integer is not None and not a str, so _require must not raise.

        This matters because TOML fields like ``id = 42`` are valid integers and
        are later coerced with str() by the caller.
        """
        _require("id", 42, "section")  # must not raise


# ---------------------------------------------------------------------------
# _parse_prompts
# ---------------------------------------------------------------------------


class TestParsePrompts:
    def test_returns_dict_when_prompts_is_a_dict(self) -> None:
        data = {"prompts": {"system_prompt": "You are helpful.", "human_prompt": "Do it."}}
        assert _parse_prompts(data) == {
            "system_prompt": "You are helpful.",
            "human_prompt": "Do it.",
        }

    def test_returns_empty_dict_when_prompts_key_is_absent(self) -> None:
        assert _parse_prompts({}) == {}

    def test_returns_empty_dict_when_prompts_is_not_a_dict(self) -> None:
        """TOML like ``prompts = "some string"`` must not raise — just return {}."""
        assert _parse_prompts({"prompts": "some string"}) == {}

    def test_coerces_non_string_prompt_values_to_str(self) -> None:
        """Non-string values (e.g. TOML integers) inside [prompts] must be coerced."""
        assert _parse_prompts({"prompts": {"answer": 42}}) == {"answer": "42"}

    def test_collapses_whitespace_only_lines_in_prompts(self) -> None:
        """Lines that contain only spaces/tabs become empty; intentional \\n\\n\\n is kept."""
        data = {
            "prompts": {
                "system_prompt": "a\n    \nb",
                "multi_space_lines": "x\n  \n  \ny",
                "triple_blank": "p\n\n\nq",
            }
        }
        assert _parse_prompts(data) == {
            "system_prompt": "a\n\nb",
            "multi_space_lines": "x\n\n\ny",
            "triple_blank": "p\n\n\nq",
        }


# ---------------------------------------------------------------------------
# load_evaluator_settings
# ---------------------------------------------------------------------------


class TestLoadEvaluatorSettings:
    def test_parses_full_toml(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[evaluator_metadata]
id = "test_evaluator"
version = "0.1"
name = "Test"
description = "Test evaluator"
maturity = "beta"

[prompts]
system_prompt = "You are a helpful assistant."

[evaluation_settings.prompt_settings_step_main]
type = "GOOGLE"
model = "gemini-2.0-flash"
temperature = 0
""",
        )
        result = load_evaluator_settings(path, ConventionalityEvaluationSettings)
        assert isinstance(result, EvaluatorSettingsResult)
        assert result.evaluator_metadata.id == "test_evaluator"
        assert result.evaluator_metadata.version == "0.1"
        assert result.evaluator_metadata.maturity == EvaluatorMaturity.beta
        assert result.prompts["system_prompt"] == "You are a helpful assistant."
        ps_main = result.evaluation_settings.prompt_settings_step_main
        assert ps_main is not None
        assert ps_main.model == "gemini-2.0-flash"
        assert ps_main.temperature == 0.0

    def test_raises_when_evaluator_metadata_section_missing(self, tmp_path: Path) -> None:
        path = _write_toml(tmp_path, _MINIMAL_EVAL_SETTINGS)
        with pytest.raises(ConfigurationError, match="evaluator_metadata"):
            load_evaluator_settings(path, ConventionalityEvaluationSettings)

    def test_raises_when_evaluation_settings_section_missing(self, tmp_path: Path) -> None:
        path = _write_toml(tmp_path, _MINIMAL_META)
        with pytest.raises(ConfigurationError, match="evaluation_settings"):
            load_evaluator_settings(path, ConventionalityEvaluationSettings)

    def test_raises_when_required_prompt_settings_field_missing(self, tmp_path: Path) -> None:
        """temperature is required in every prompt_settings_* step; omitting it must raise."""
        path = _write_toml(
            tmp_path,
            _MINIMAL_META
            + """
[evaluation_settings.prompt_settings_step_main]
type = "GOOGLE"
model = "gemini-2.0-flash"
""",
        )
        with pytest.raises(ConfigurationError, match="temperature"):
            load_evaluator_settings(path, ConventionalityEvaluationSettings)

    def test_raises_for_invalid_maturity_value(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[evaluator_metadata]
id = "x"
version = "0.1"
name = "X"
description = "X"
maturity = "not_a_real_maturity"
"""
            + _MINIMAL_EVAL_SETTINGS,
        )
        with pytest.raises(ConfigurationError, match="maturity"):
            load_evaluator_settings(path, ConventionalityEvaluationSettings)

    def test_raises_for_invalid_provider_type(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            _MINIMAL_META
            + """
[evaluation_settings.prompt_settings_step_main]
type = "INVALID_PROVIDER"
model = "some-model"
temperature = 0
""",
        )
        with pytest.raises(ConfigurationError, match="provider"):
            load_evaluator_settings(path, ConventionalityEvaluationSettings)

    def test_parses_inputs_into_typed_specs(self, tmp_path: Path) -> None:
        """[[evaluator_metadata.inputs]] entries become TextInputSpec / GradeInputSpec."""
        from learning_commons_evaluators.schemas.input_specs import (
            GradeInputSpec,
            TextInputSpec,
        )

        path = _write_toml(
            tmp_path,
            """
[evaluator_metadata]
id = "x"
version = "0.1"
name = "X"
description = "X"
maturity = "beta"

[[evaluator_metadata.inputs]]
name = "text"
type = "TextInputField"
min_text_length = 50
max_text_length = 5000

[[evaluator_metadata.inputs]]
name = "grade"
type = "GradeInputField"
allowed_grades = [3, 4, 5, 6]

[evaluation_settings.prompt_settings_step_main]
type = "GOOGLE"
model = "gemini-2.0-flash"
temperature = 0
""",
        )
        result = load_evaluator_settings(path, ConventionalityEvaluationSettings)
        inputs = result.evaluator_metadata.inputs

        text_spec = inputs["text"]
        assert isinstance(text_spec, TextInputSpec)
        assert text_spec.min_text_length == 50
        assert text_spec.max_text_length == 5000

        grade_spec = inputs["grade"]
        assert isinstance(grade_spec, GradeInputSpec)
        assert grade_spec.allowed_grades == [3, 4, 5, 6]

    def test_raises_for_unknown_input_type(self, tmp_path: Path) -> None:
        path = _write_toml(
            tmp_path,
            """
[evaluator_metadata]
id = "x"
version = "0.1"
name = "X"
description = "X"
maturity = "beta"

[[evaluator_metadata.inputs]]
name = "mystery"
type = "UnknownInputField"

[evaluation_settings.prompt_settings_step_main]
type = "GOOGLE"
model = "gemini-2.0-flash"
temperature = 0
""",
        )
        with pytest.raises(ConfigurationError, match="Unknown input type"):
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
        assert root.exists(), f"shared_settings_root() resolved to non-existent path: {root}"

    def test_bundled_contract_tests_are_present(self) -> None:
        """The bundled package must contain contracts.toml for each evaluator.

        The evaluator settings TOML is intentionally NOT bundled (evaluators use _generated_*_settings.py).
        contracts.toml IS bundled so contract tests work against an installed package.
        """
        env = {k: v for k, v in os.environ.items() if k != "EVALUATORS_SETTINGS_DIR"}
        with patch.dict(os.environ, env, clear=True):
            root = shared_settings_root()
        for evaluator in ("conventionality",):
            assert (root / evaluator / "contracts.toml").exists(), (
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


@pytest.mark.parametrize("evaluator", ["conventionality"])
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
