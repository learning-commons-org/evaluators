"""Load evaluator settings from TOML files."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from importlib.abc import Traversable
else:
    # Runtime location moved to importlib.resources.abc in newer Python versions,
    # while mypy's Python 3.10 types expose Traversable from importlib.abc.
    try:
        from importlib.resources.abc import Traversable
    except ImportError:
        from importlib.abc import Traversable

if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

from pydantic import TypeAdapter
from pydantic import ValidationError as PydanticValidationError

from learning_commons_evaluators.schemas.config import EvaluationSettings, PromptSettings
from learning_commons_evaluators.schemas.errors import ConfigurationError
from learning_commons_evaluators.schemas.metadata import EvaluatorMetadata

T = TypeVar("T", bound=EvaluationSettings)


def shared_settings_root() -> Path | Traversable:
    """Return the evaluator settings directory (filesystem or package Traversable).

    Resolution order:

    1. ``EVALUATORS_SETTINGS_DIR`` environment variable — point this at the
       ``sdks/settings/`` directory when working inside the monorepo so the
       SDK reads the shared copy (shared with TypeScript and other SDKs)
       rather than the bundled copy inside the package::

           export EVALUATORS_SETTINGS_DIR=/path/to/evaluators/sdks/settings

       Also useful in CI jobs that check out settings separately.

    2. Bundled package data — a :class:`importlib.abc.Traversable` from
       :func:`importlib.resources.files` for the ``learning_commons_evaluators.settings``
       sub-package (works from a wheel/zip without assuming a real directory path).

       Use :func:`load_settings` / :func:`load_evaluator_settings`, which accept a
       ``Traversable``, or :func:`importlib.resources.as_file` if an API requires a
       concrete :class:`pathlib.Path` on disk.

    The bundled copy is kept in sync with ``sdks/settings/`` — see the
    *Keeping settings in sync* section of the README.
    """
    env = os.environ.get("EVALUATORS_SETTINGS_DIR")
    if env:
        return Path(env)
    return resources.files("learning_commons_evaluators.settings")


def load_settings(path: Path | str | Traversable) -> dict:
    """
    Load raw settings from a TOML file.

    Args:
        path: Path to the .toml file, or a :class:`~importlib.abc.Traversable`
            (e.g. from :func:`shared_settings_root` when using bundled settings).

    Returns:
        Parsed TOML as a dict.
    """
    if isinstance(path, Traversable):
        with path.open("rb") as f:
            return tomllib.load(f)
    with Path(path).open("rb") as f:
        return tomllib.load(f)


_prompt_settings_adapter = TypeAdapter(PromptSettings)


def _prepare_prompt_settings_dict(pm: dict) -> dict:
    """Lowercase ``provider_type`` strings for TOML / enum matching."""
    d = dict(pm)
    pt = d.get("provider_type")
    if isinstance(pt, str):
        d["provider_type"] = pt.lower().strip()
    return d


def _validated_prompt_settings(pm: dict, step_name: str) -> PromptSettings:
    try:
        return _prompt_settings_adapter.validate_python(_prepare_prompt_settings_dict(pm))
    except PydanticValidationError as e:
        raise ConfigurationError(f"Invalid [{step_name}]: {e}") from e


def _parse_evaluator_metadata(data: dict) -> EvaluatorMetadata:
    """Build EvaluatorMetadata from TOML ``[evaluator_metadata]`` via Pydantic validation."""
    em = data.get("evaluator_metadata")
    if not em or not isinstance(em, dict):
        raise ConfigurationError("Missing required section [evaluator_metadata].")
    try:
        return EvaluatorMetadata.model_validate(em)
    except PydanticValidationError as e:
        raise ConfigurationError(f"Invalid [evaluator_metadata]: {e}") from e


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
    """Build prompts dict from TOML ``[prompts]`` section. Optional; values must be strings."""
    prompts_section = data.get("prompts")
    if prompts_section is None or not isinstance(prompts_section, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in prompts_section.items():
        if not isinstance(v, str):
            raise ConfigurationError(
                f"Invalid [prompts].{k}: expected a string prompt, got {type(v).__name__}."
            )
        out[k] = _normalize_prompt_whitespace(v)
    return out


@dataclass(frozen=True)
class EvaluatorSettingsResult(Generic[T]):
    """Result of loading an evaluator TOML: metadata, typed evaluation settings, and prompt templates."""

    evaluator_metadata: EvaluatorMetadata
    evaluation_settings: T
    prompts: dict[str, str]


def load_evaluator_settings(
    path: Path | str | Traversable, settings_cls: type[T]
) -> EvaluatorSettingsResult[T]:
    """
    Load evaluator settings from a TOML file.

    Parses evaluator_metadata into EvaluatorMetadata, evaluation_settings into an instance
    of settings_cls (with ``prompt_settings_*`` subsections as :class:`~learning_commons_evaluators.schemas.config.PromptSettings`
    using ``provider_type``, ``model``, and ``temperature``), and extracts
    prompt text (e.g. system_prompt) into a prompts dict. Raises ConfigurationError if
    any required field or section is missing.

    Args:
        path: Path to the .toml file, or a :class:`~importlib.abc.Traversable` to it.
        settings_cls: Class for evaluation settings (e.g. ConventionalityEvaluationSettings).
            Must be a Pydantic :class:`~pydantic.BaseModel` subclass; validated with ``model_validate``.

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
            raw[key] = _validated_prompt_settings(raw[key], f"evaluation_settings.{key}")

    try:
        evaluation_settings = settings_cls.model_validate(raw)
    except PydanticValidationError as e:
        raise ConfigurationError(f"Invalid [evaluation_settings]: {e}") from e

    return EvaluatorSettingsResult(
        evaluator_metadata=evaluator_metadata,
        evaluation_settings=evaluation_settings,
        prompts=prompts,
    )
