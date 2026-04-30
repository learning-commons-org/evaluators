#!/usr/bin/env python3
"""Generate pre-built settings modules from evaluator TOML files.

Each evaluator's settings TOML is parsed once at *build time* and serialised
as a plain Python module.  The evaluator modules then import that generated
module at import time — no file I/O, no TOML parsing on every process start.

Each evaluator directory under sdks/settings/ contains two files::

    sdks/settings/<evaluator>/settings.toml   — prompts, model, temperature
    sdks/settings/<evaluator>/contracts.toml  — captured LLM interactions for contract tests

Usage::

    # Regenerate all evaluators:
    python scripts/generate_settings.py

    # Check whether generated files are stale (exits 1 if any differ):
    python scripts/generate_settings.py --check

    # Copy contracts.toml from sdks/settings/ → bundled package:
    python scripts/generate_settings.py --sync

    # Verify bundled contracts.toml matches canonical sdks/settings/:
    python scripts/generate_settings.py --check-sync

Typical CI configuration::

    - name: Check settings are up to date
      run: python scripts/generate_settings.py --check
    - name: Check contracts are in sync
      run: python scripts/generate_settings.py --check-sync

When to regenerate::

    Any time you edit settings.toml under sdks/settings/<evaluator>/,
    run this script and commit the updated generated file alongside the TOML.
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys
import types
from dataclasses import MISSING, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — resolve repo root and add SDK src to sys.path so we can import
# the SDK without a full install.
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
_SDK_SRC = _REPO_ROOT / "sdks" / "python" / "src"
_SETTINGS_DIR = _REPO_ROOT / "sdks" / "settings"
_GENERATED_DIR = _SDK_SRC / "learning_commons_evaluators" / "settings"

sys.path.insert(0, str(_SDK_SRC))

# Point load_settings at the canonical settings directory so the generator
# always reads the source-of-truth TOML, not the bundled copy.
os.environ.setdefault("EVALUATORS_SETTINGS_DIR", str(_SETTINGS_DIR))

# Pre-register the package without running learning_commons_evaluators/__init__.py.
# That __init__ imports evaluators, which import generated settings — invalid while
# this script is regenerating those files. Submodules (schemas, settings, …) load
# normally via __path__.
if "learning_commons_evaluators" not in sys.modules:
    _lce_pkg = types.ModuleType("learning_commons_evaluators")
    _lce_pkg.__path__ = [str(_SDK_SRC / "learning_commons_evaluators")]
    sys.modules["learning_commons_evaluators"] = _lce_pkg

# ---------------------------------------------------------------------------
# SDK imports (after path setup)
# ---------------------------------------------------------------------------

from pydantic import BaseModel  # noqa: E402
from pydantic_core import PydanticUndefined  # noqa: E402

from learning_commons_evaluators.schemas.config import (  # noqa: E402
    EvaluationSettings,
)
from learning_commons_evaluators.schemas.conventionality import (  # noqa: E402
    ConventionalityEvaluationSettings,
)
from learning_commons_evaluators.schemas.vocabulary import (  # noqa: E402
    VocabularyEvaluationSettings,
)
from learning_commons_evaluators.settings.load_settings import (  # noqa: E402
    EvaluatorSettingsResult,
    load_evaluator_settings,
)

# ---------------------------------------------------------------------------
# Import map: class name → (module path, symbol name)
# Used to build the import block of generated files.
# ---------------------------------------------------------------------------

_IMPORT_MAP: dict[str, tuple[str, str]] = {
    "ConventionalityEvaluationSettings": (
        "learning_commons_evaluators.schemas.conventionality",
        "ConventionalityEvaluationSettings",
    ),
    "EvaluatorMaturity": (
        "learning_commons_evaluators.schemas.metadata",
        "EvaluatorMaturity",
    ),
    "EvaluatorMetadata": (
        "learning_commons_evaluators.schemas.metadata",
        "EvaluatorMetadata",
    ),
    "EvaluatorSettingsResult": (
        "learning_commons_evaluators.settings.load_settings",
        "EvaluatorSettingsResult",
    ),
    "GradeInputSpec": (
        "learning_commons_evaluators.schemas.input_specs",
        "GradeInputSpec",
    ),
    "LlmProvider": (
        "learning_commons_evaluators.schemas.config",
        "LlmProvider",
    ),
    "PromptSettings": (
        "learning_commons_evaluators.schemas.config",
        "PromptSettings",
    ),
    "TextInputSpec": (
        "learning_commons_evaluators.schemas.input_specs",
        "TextInputSpec",
    ),
    "VocabularyEvaluationSettings": (
        "learning_commons_evaluators.schemas.vocabulary",
        "VocabularyEvaluationSettings",
    ),
}

# ---------------------------------------------------------------------------
# Value emitter
# ---------------------------------------------------------------------------


def _emit_string(s: str) -> str:
    """Emit a string literal, using triple-quotes for multiline / long strings."""
    if "\n" in s or len(s) > 88:
        # Escape any literal `"""` sequences inside the content.
        content = s.replace('"""', '""\\"')
        return f'"""{content}"""'
    return repr(s)


def _emit_value(obj: Any, indent: int = 0) -> str:
    """Recursively emit a Python value as a source-code string."""
    pad = "    " * indent
    inner = "    " * (indent + 1)

    if obj is None:
        return "None"
    if isinstance(obj, bool):
        return "True" if obj else "False"
    # str- and int-backed enums (e.g. LlmProvider(str, Enum)) must be handled before
    # str/int or we emit repr() and get invalid syntax like <LlmProvider.GOOGLE: 'google'>.
    if isinstance(obj, Enum):
        return f"{type(obj).__name__}.{obj.name}"
    if isinstance(obj, int):
        return repr(obj)
    if isinstance(obj, float):
        return f"{obj:.1f}" if obj == int(obj) else repr(obj)
    if isinstance(obj, str):
        return _emit_string(obj)
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = [_emit_value(v, indent + 1) for v in obj]
        single = f"[{', '.join(items)}]"
        if len(single) <= 88 - len(pad) and "\n" not in single:
            return single
        body = "\n".join(f"{inner}{item}," for item in items)
        return f"[\n{body}\n{pad}]"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        pairs = [(repr(k), _emit_value(v, indent + 1)) for k, v in obj.items()]
        single = "{" + ", ".join(f"{k}: {v}" for k, v in pairs) + "}"
        if len(single) <= 88 - len(pad) and "\n" not in single:
            return single
        body = "\n".join(f"{inner}{k}: {v}," for k, v in pairs)
        return f"{{\n{body}\n{pad}}}"
    if is_dataclass(obj) and not isinstance(obj, type):
        return _emit_dataclass(obj, indent)
    if isinstance(obj, BaseModel):
        return _emit_model(obj, indent)
    raise TypeError(f"Cannot emit {type(obj).__name__}: {obj!r}")


def _emit_model(obj: BaseModel, indent: int = 0) -> str:
    """Emit a Pydantic model as a constructor call."""
    cls = type(obj)
    cls_name = cls.__name__
    pad = "    " * indent
    inner = "    " * (indent + 1)

    args: list[tuple[str, str]] = []
    for field_name, field_info in cls.model_fields.items():
        val = getattr(obj, field_name)

        # Skip Literal discriminators (e.g. type="TextInputField").
        if field_name == "type" and not field_info.is_required():
            continue

        # Skip fields that equal their default — keeps generated code clean.
        default = field_info.default
        if default is not PydanticUndefined and val == default:
            continue

        args.append((field_name, _emit_value(val, indent + 1)))

    if not args:
        return f"{cls_name}()"

    single = f"{cls_name}({', '.join(f'{n}={v}' for n, v in args)})"
    if len(single) <= 88 - len(pad) and "\n" not in single:
        return single

    body = "\n".join(f"{inner}{n}={v}," for n, v in args)
    return f"{cls_name}(\n{body}\n{pad})"


def _emit_dataclass(obj: Any, indent: int = 0) -> str:
    """Emit a stdlib dataclass instance as a constructor call (e.g. PromptSettings)."""
    cls = type(obj)
    cls_name = cls.__name__
    pad = "    " * indent
    inner = "    " * (indent + 1)

    args: list[tuple[str, str]] = []
    for f in fields(obj):
        val = getattr(obj, f.name)
        if f.default is not MISSING and val == f.default:
            continue
        args.append((f.name, _emit_value(val, indent + 1)))

    if not args:
        return f"{cls_name}()"

    single = f"{cls_name}({', '.join(f'{n}={v}' for n, v in args)})"
    if len(single) <= 88 - len(pad) and "\n" not in single:
        return single

    body = "\n".join(f"{inner}{n}={v}," for n, v in args)
    return f"{cls_name}(\n{body}\n{pad})"


# ---------------------------------------------------------------------------
# Import-block builder
# ---------------------------------------------------------------------------


def _collect_class_names(obj: Any, names: set[str]) -> None:
    """Walk obj recursively and collect names of all classes that need importing."""
    if isinstance(obj, Enum):
        names.add(type(obj).__name__)
    elif is_dataclass(obj) and not isinstance(obj, type):
        names.add(type(obj).__name__)
        for f in fields(obj):
            _collect_class_names(getattr(obj, f.name), names)
    elif isinstance(obj, BaseModel):
        names.add(type(obj).__name__)
        for field_name in type(obj).model_fields:
            _collect_class_names(getattr(obj, field_name), names)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_class_names(v, names)
    elif isinstance(obj, list):
        for v in obj:
            _collect_class_names(v, names)


def _build_import_block(config: EvaluatorSettingsResult, settings_cls_name: str) -> str:
    used: set[str] = set()
    _collect_class_names(config.evaluator_metadata, used)
    _collect_class_names(config.evaluation_settings, used)
    used.add(settings_cls_name)
    used.add("EvaluatorSettingsResult")

    by_module: dict[str, list[str]] = {}
    for name in sorted(used):
        if name in _IMPORT_MAP:
            mod, sym = _IMPORT_MAP[name]
            by_module.setdefault(mod, []).append(sym)

    lines: list[str] = []
    for mod in sorted(by_module):
        syms = sorted(by_module[mod])
        if len(syms) == 1:
            lines.append(f"from {mod} import {syms[0]}")
        else:
            lines.append(f"from {mod} import {', '.join(syms)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# File generator
# ---------------------------------------------------------------------------


def generate_module(
    evaluator_name: str,
    toml_path: Path,
    settings_cls: type[EvaluationSettings],
) -> str:
    """Parse *toml_path* and return the content of the generated Python module."""
    config = load_evaluator_settings(toml_path, settings_cls)
    settings_cls_name = settings_cls.__name__

    imports = _build_import_block(config, settings_cls_name)
    metadata_code = _emit_model(config.evaluator_metadata)
    prompts_code = _emit_value(config.prompts)
    settings_code = _emit_model(config.evaluation_settings)

    rel_toml = toml_path.relative_to(_REPO_ROOT)

    # Emit flush-left Python only. Do not wrap this in textwrap.dedent() while
    # interpolating multi-line fragments (imports, *_code): continuation lines
    # from those values start at column 0, which would make dedent's common
    # margin zero and leave the header indented — IndentationError at import.
    return f"""# !! AUTO-GENERATED — do not edit directly.
# Source: {rel_toml}
# Regenerate : python scripts/generate_settings.py
# Staleness check: python scripts/generate_settings.py --check

from __future__ import annotations

{imports}

# ── Evaluator metadata ────────────────────────────────────────────────────────

_EVALUATOR_METADATA = {metadata_code}

# ── Prompt templates ──────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = {prompts_code}

# ── Evaluation settings ───────────────────────────────────────────────────────

_EVALUATION_SETTINGS = {settings_code}

# ── Public config object (imported by evaluator modules) ──────────────────────

CONFIG: EvaluatorSettingsResult[{settings_cls_name}] = EvaluatorSettingsResult(
    evaluator_metadata=_EVALUATOR_METADATA,
    evaluation_settings=_EVALUATION_SETTINGS,
    prompts=_PROMPTS,
)
"""


# ---------------------------------------------------------------------------
# Evaluator registry
# ---------------------------------------------------------------------------

_EVALUATORS: list[dict] = [
    {
        "name": "conventionality",
        "settings_cls": ConventionalityEvaluationSettings,
        "output": _GENERATED_DIR / "_generated_conventionality_settings.py",
    },
    {
        "name": "vocabulary",
        "settings_cls": VocabularyEvaluationSettings,
        "output": _GENERATED_DIR / "_generated_vocabulary_settings.py",
    },
]


def _settings_toml(evaluator_name: str) -> Path:
    """Return ``sdks/settings/<evaluator>/settings.toml``."""
    return _SETTINGS_DIR / evaluator_name / "settings.toml"


def _contracts_toml(evaluator_name: str) -> Path:
    """Return the canonical ``sdks/settings/<evaluator>/contracts.toml``."""
    return _SETTINGS_DIR / evaluator_name / "contracts.toml"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_generate() -> None:
    for ev in _EVALUATORS:
        content = generate_module(ev["name"], _settings_toml(ev["name"]), ev["settings_cls"])
        ev["output"].write_text(content, encoding="utf-8")
        rel = ev["output"].relative_to(_REPO_ROOT)
        print(f"  generated  {rel}")
    print("Done.")


def cmd_check() -> int:
    stale: list[str] = []
    for ev in _EVALUATORS:
        expected = generate_module(ev["name"], _settings_toml(ev["name"]), ev["settings_cls"])
        actual = ev["output"].read_text(encoding="utf-8") if ev["output"].exists() else ""
        if expected != actual:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=str(ev["output"].relative_to(_REPO_ROOT)),
                    tofile="(regenerated)",
                    n=3,
                )
            )
            print(f"STALE: {ev['output'].relative_to(_REPO_ROOT)}\n{diff}")
            stale.append(ev["name"])

    if stale:
        print(f"\nStale evaluators: {stale}")
        print("Run:  python scripts/generate_settings.py")
        return 1

    print("All generated settings are up to date.")
    return 0


def cmd_sync() -> None:
    """Copy ``contracts.toml`` from canonical (sdks/settings/) → bundled package.

    The bundled package ships a copy of the contracts TOML so that contract
    tests work correctly when installed via ``pip install`` (i.e. without
    access to the monorepo ``sdks/settings/`` directory).
    """
    for ev in _EVALUATORS:
        src = _contracts_toml(ev["name"])
        if not src.exists():
            print(f"  WARNING: canonical {src.relative_to(_REPO_ROOT)} not found — skipping")
            continue
        dst_dir = _GENERATED_DIR / ev["name"]
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "contracts.toml"
        dst.write_bytes(src.read_bytes())
        print(f"  copied   {src.relative_to(_REPO_ROOT)} → {dst.relative_to(_REPO_ROOT)}")
    print("Done.")


def cmd_check_sync() -> int:
    """Verify bundled ``contracts.toml`` files match the canonical sdks/settings/ copies.

    Exits with a non-zero status if any bundled file is missing or differs from
    the canonical source.
    """
    errors: list[str] = []
    for ev in _EVALUATORS:
        canonical = _contracts_toml(ev["name"])
        if not canonical.exists():
            errors.append(f"MISSING canonical: {canonical.relative_to(_REPO_ROOT)}")
            continue
        bundled = _GENERATED_DIR / ev["name"] / "contracts.toml"
        if not bundled.exists():
            errors.append(
                f"MISSING bundled: {bundled.relative_to(_REPO_ROOT)} "
                f"(run: python scripts/generate_settings.py --sync)"
            )
        elif canonical.read_bytes() != bundled.read_bytes():
            errors.append(
                f"OUT OF SYNC: {ev['name']}/contracts.toml "
                f"(run: python scripts/generate_settings.py --sync)"
            )

    if errors:
        for msg in errors:
            print(msg)
        return 1

    print("All contracts TOMLs are in sync.")
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Generate (or check) pre-built settings modules from evaluator TOML files, "
            "and sync bundled contracts TOMLs."
        )
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Check generated _generated_*_settings.py files for staleness; "
            "exit 1 if any differ from what would be generated."
        ),
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help=(
            "Copy contracts.toml from sdks/settings/ into the bundled package "
            "directory so contract tests work after pip install."
        ),
    )
    parser.add_argument(
        "--check-sync",
        action="store_true",
        dest="check_sync",
        help=(
            "Verify bundled contracts.toml files match the canonical sdks/settings/ "
            "copies; exit 1 if any are missing or differ."
        ),
    )
    args = parser.parse_args()

    if args.check:
        sys.exit(cmd_check())
    elif args.sync:
        cmd_sync()
    elif args.check_sync:
        sys.exit(cmd_check_sync())
    else:
        cmd_generate()


if __name__ == "__main__":
    main()
