"""Load evaluator settings from TOML files."""

from __future__ import annotations

import importlib.resources
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Generic, TypeVar, cast

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]  # Python < 3.11

from learning_commons_evaluators.schemas.config import LlmProvider, PromptSettings
from learning_commons_evaluators.schemas.errors import ConfigurationError
from learning_commons_evaluators.schemas.input_specs import (
    INPUT_SPEC_REGISTRY,
    AnyInputSpec,
)
from learning_commons_evaluators.schemas.metadata import (
    EvaluatorMaturity,
    EvaluatorMetadata,
)

T = TypeVar("T")


def shared_settings_root() -> Path:
    """Return the path to the evaluator settings directory.

    Resolution order:

    1. ``EVALUATORS_SETTINGS_DIR`` environment variable — point this at the
       ``sdks/settings/`` directory when working inside the monorepo so the
       SDK reads the shared copy (shared with TypeScript and other SDKs)
       rather than the bundled copy inside the package::

           export EVALUATORS_SETTINGS_DIR=/path/to/evaluators/sdks/settings

       Also useful in CI jobs that check out settings separately.

    2. Bundled package data — resolved via :mod:`importlib.resources` from the
       ``learning_commons_evaluators.settings`` sub-package.  This is the path
       taken by a normal ``pip install`` (editable or non-editable) when the
       env var is not set.

    The bundled copy is kept in sync with ``sdks/settings/`` — see the
    *Keeping settings in sync* section of the README.
    """
    env = os.environ.get("EVALUATORS_SETTINGS_DIR")
    if env:
        return Path(env)
    # importlib.resources.files() returns a Traversable; converting to Path
    # works for both editable installs (a real directory) and zip/wheel installs
    # (where Python 3.9+ extracts to a temp dir automatically).
    pkg = importlib.resources.files("learning_commons_evaluators.settings")
    return Path(str(pkg))


def _require(key: str, value: object, section: str) -> None:
    """Raise ConfigurationError if value is missing or empty."""
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ConfigurationError(f"Missing required field '{key}' in [{section}]")


def load_settings(path: Path | str) -> dict:
    """
    Load raw settings from a TOML file.

    Args:
        path: Path to the .toml file.

    Returns:
        Parsed TOML as a dict.
    """
    path = Path(path)
    with path.open("rb") as f:
        return tomllib.load(f)


def _parse_maturity(value: str) -> EvaluatorMaturity:
    """Map TOML maturity string to EvaluatorMaturity enum."""
    try:
        return EvaluatorMaturity(value.lower())
    except ValueError as e:
        raise ConfigurationError(
            f"Invalid maturity '{value}' in [evaluator_metadata]; expected one of alpha, beta, rc, ga."
        ) from e


def _parse_evaluator_metadata(data: dict) -> EvaluatorMetadata:
    """Build EvaluatorMetadata from TOML evaluator_metadata section. Raises ConfigurationError if a required field is missing."""
    em = data.get("evaluator_metadata")
    if not em or not isinstance(em, dict):
        raise ConfigurationError("Missing required section [evaluator_metadata].")
    section = "evaluator_metadata"
    id_val = em.get("id")
    _require("id", id_val, section)
    version = em.get("version")
    _require("version", version, section)
    if not isinstance(version, str):
        version = str(version)
    name = em.get("name")
    _require("name", name, section)
    description = em.get("description")
    _require("description", description, section)
    maturity_val = em.get("maturity")
    _require("maturity", maturity_val, section)
    if not isinstance(maturity_val, str):
        raise ConfigurationError(f"Field 'maturity' in [{section}] must be a string.")
    maturity = _parse_maturity(maturity_val)
    # Parse [[evaluator_metadata.inputs]] into a dict keyed by field name.
    # Dispatch on ``type`` to create the correct InputSpec subclass so that
    # type-specific constraint fields (e.g. min_text_length) are preserved.
    inputs: dict[str, AnyInputSpec] = {}
    for spec_dict in em.get("inputs", []):
        if not (isinstance(spec_dict, dict) and "name" in spec_dict):
            continue
        field_name = spec_dict["name"]
        type_key = spec_dict.get("type", "")
        spec_cls = INPUT_SPEC_REGISTRY.get(type_key)
        if spec_cls is None:
            raise ConfigurationError(
                f"Unknown input type '{type_key}' in [[evaluator_metadata.inputs]] "
                f"for field '{field_name}'. Expected one of: {sorted(INPUT_SPEC_REGISTRY)}."
            )
        inputs[field_name] = cast(AnyInputSpec, spec_cls(**spec_dict))

    return EvaluatorMetadata(
        id=str(id_val).strip(),
        version=version.strip(),
        name=str(name).strip(),
        description=str(description).strip(),
        maturity=maturity,
        inputs=inputs,
    )


def _parse_provider_type(value: str, step_name: str) -> LlmProvider:
    """Map TOML provider type string to LlmProvider enum."""
    normalized = value.upper().strip()
    if normalized == "GOOGLE":
        return LlmProvider.GOOGLE
    if normalized == "OPENAI":
        return LlmProvider.OPENAI
    if normalized == "ANTHROPIC":
        return LlmProvider.ANTHROPIC
    raise ConfigurationError(
        f"Invalid provider type '{value}' in [{step_name}]; expected one of: google, openai, anthropic."
    )


def _parse_prompt_settings_step(pm: dict, step_name: str) -> PromptSettings:
    """Build PromptSettings from a TOML prompt_settings_* subsection. Raises ConfigurationError if a required field is missing."""
    pt = pm.get("type") or pm.get("provider_type")
    _require("type", pt, step_name)
    if not isinstance(pt, str):
        raise ConfigurationError(f"Field 'type' in [{step_name}] must be a string.")
    provider_type = _parse_provider_type(pt, step_name)
    model = pm.get("model")
    _require("model", model, step_name)
    if not isinstance(model, str):
        raise ConfigurationError(f"Field 'model' in [{step_name}] must be a string.")
    temp = pm.get("temperature")
    if temp is None:
        raise ConfigurationError(f"Missing required field 'temperature' in [{step_name}].")
    try:
        temperature = float(temp)
    except (TypeError, ValueError) as e:
        raise ConfigurationError(f"Field 'temperature' in [{step_name}] must be a number.") from e
    return PromptSettings(
        provider_type=provider_type,
        model=model.strip(),
        temperature=temperature,
    )


def _normalize_prompt_whitespace(prompt: str) -> str:
    """Turn whitespace-only lines into empty lines (TOML indentation quirk).

    Multiline TOML often uses lines that contain only spaces so blank rows align with
    indented text; editors and notebook capture usually use truly empty lines instead.
    Each whitespace-only line becomes empty; runs of already-empty lines are left
    unchanged so prompts can keep extra vertical gaps where intended.
    """
    lines = prompt.split("\n")
    return "\n".join("" if (line != "" and line.strip() == "") else line for line in lines)


def _parse_prompts(data: dict) -> dict[str, str]:
    """Build prompts dict from TOML [prompts] section. Optional; any string values are included."""
    prompts_section = data.get("prompts")
    if prompts_section is None or not isinstance(prompts_section, dict):
        return {}
    return {
        k: _normalize_prompt_whitespace(v if isinstance(v, str) else str(v))
        for k, v in prompts_section.items()
    }


@dataclass(frozen=True)
class EvaluatorSettingsResult(Generic[T]):
    """Result of loading an evaluator TOML: metadata, typed evaluation settings, and prompt templates."""

    evaluator_metadata: EvaluatorMetadata
    evaluation_settings: T
    prompts: dict[str, str]


def load_evaluator_settings(path: Path | str, settings_cls: type[T]) -> EvaluatorSettingsResult[T]:
    """
    Load evaluator settings from a TOML file.

    Parses evaluator_metadata into EvaluatorMetadata, evaluation_settings into an instance
    of settings_cls (with prompt_settings_* subsections as PromptSettings), and extracts
    prompt text (e.g. system_prompt) into a prompts dict. Raises ConfigurationError if
    any required field or section is missing.

    Args:
        path: Path to the .toml file.
        settings_cls: Class for evaluation settings (e.g. ConventionalityEvaluationSettings).
            Must accept keyword arguments matching the TOML evaluation_settings keys.

    Returns:
        EvaluatorSettingsResult with evaluator_metadata, evaluation_settings (typed), and prompts.
    """
    data = load_settings(path)
    evaluator_metadata = _parse_evaluator_metadata(data)

    prompts = _parse_prompts(data)

    raw = data.get("evaluation_settings")
    if raw is None or not isinstance(raw, dict):
        raise ConfigurationError("Missing required section [evaluation_settings].")
    raw = dict(raw)

    # Convert prompt_settings_* subsections to PromptSettings.
    for key in list(raw):
        if key.startswith("prompt_settings_") and isinstance(raw[key], dict):
            raw[key] = _parse_prompt_settings_step(raw[key], f"evaluation_settings.{key}")

    try:
        evaluation_settings = settings_cls(**raw)
    except Exception as e:
        if isinstance(e, ConfigurationError):
            raise
        raise ConfigurationError(
            f"Invalid [evaluation_settings]: {e!s}",
        ) from e

    return EvaluatorSettingsResult(
        evaluator_metadata=evaluator_metadata,
        evaluation_settings=evaluation_settings,
        prompts=prompts,
    )
