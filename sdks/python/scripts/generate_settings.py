#!/usr/bin/env python3
"""Generate pre-built settings modules from evaluator TOML files.

Each evaluator's settings TOML is parsed once at *build time* and serialised
as a plain Python module.  The evaluator modules then import that generated
module at import time — no file I/O, no TOML parsing on every process start.

Each evaluator directory under sdks/settings/ that contains ``settings.toml`` is picked up
automatically.  The settings model is resolved as::

    learning_commons_evaluators.schemas.<evaluator>.<PascalCase>EvaluationSettings

where ``<PascalCase>`` is the snake_case evaluator folder name converted to PascalCase
(e.g. ``conventionality`` → ``ConventionalityEvaluationSettings`` in
``schemas.conventionality``).

Each such directory typically also has::

    sdks/settings/<evaluator>/contracts.toml  — captured LLM interactions for contract tests

Usage (from ``sdks/python/``, e.g. after ``cd sdks/python`` or ``make generate-settings``)::

    python scripts/generate_settings.py

From the repository root::

    python sdks/python/scripts/generate_settings.py

Other flags::

    # Check whether generated files are stale (exits 1 if any differ):
    python scripts/generate_settings.py --check

    # Copy contracts.toml from sdks/settings/ → bundled package:
    python scripts/generate_settings.py --sync

    # Verify bundled contracts.toml matches canonical sdks/settings/:
    python scripts/generate_settings.py --check-sync

Typical CI configuration (``working-directory: sdks/python``)::

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
import importlib
import os
import sys
import types
from dataclasses import MISSING, dataclass, fields, is_dataclass
from enum import Enum
from pathlib import Path
from string import Template
from typing import Any

# ---------------------------------------------------------------------------
# Path setup — resolve repo root and add SDK src to sys.path so we can import
# the SDK without a full install.  This file lives under sdks/python/scripts/.
# ---------------------------------------------------------------------------

_SCRIPT_DIR = Path(__file__).resolve().parent
_PYTHON_SDK_ROOT = _SCRIPT_DIR.parent
_REPO_ROOT = _PYTHON_SDK_ROOT.parent.parent
_SDK_SRC = _PYTHON_SDK_ROOT / "src"
_SETTINGS_DIR = _REPO_ROOT / "sdks" / "settings"
_GENERATED_DIR = _SDK_SRC / "learning_commons_evaluators" / "settings"

_LINE_WRAP = 88

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
from learning_commons_evaluators.settings.load_settings import (  # noqa: E402
    EvaluatorSettingsResult,
    load_evaluator_settings,
)

_LCE_PACKAGE = "learning_commons_evaluators"

# ---------------------------------------------------------------------------
# Emit Python source literals (no third-party codegen: must handle Enum,
# Pydantic, stdlib dataclass, and readable wrapping).
# ---------------------------------------------------------------------------


def _emit_string(s: str) -> str:
    """Emit a string literal, using triple-quotes for multiline / long strings."""
    if "\n" in s or len(s) > _LINE_WRAP:
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
        if len(single) <= _LINE_WRAP - len(pad) and "\n" not in single:
            return single
        body = "\n".join(f"{inner}{item}," for item in items)
        return f"[\n{body}\n{pad}]"
    if isinstance(obj, dict):
        if not obj:
            return "{}"
        pairs = [(repr(k), _emit_value(v, indent + 1)) for k, v in obj.items()]
        single = "{" + ", ".join(f"{k}: {v}" for k, v in pairs) + "}"
        if len(single) <= _LINE_WRAP - len(pad) and "\n" not in single:
            return single
        body = "\n".join(f"{inner}{k}: {v}," for k, v in pairs)
        return f"{{\n{body}\n{pad}}}"
    if is_dataclass(obj) and not isinstance(obj, type):
        return _emit_dataclass(obj, indent)
    if isinstance(obj, BaseModel):
        return _emit_model(obj, indent)
    raise TypeError(f"Cannot emit {type(obj).__name__}: {obj!r}")


def _format_constructor(cls_name: str, kw_args: list[tuple[str, str]], indent: int) -> str:
    """Format ``ClsName(a=..., b=...)`` with optional line wrapping."""
    pad = "    " * indent
    inner = "    " * (indent + 1)
    if not kw_args:
        return f"{cls_name}()"
    single = f"{cls_name}({', '.join(f'{n}={v}' for n, v in kw_args)})"
    if len(single) <= _LINE_WRAP - len(pad) and "\n" not in single:
        return single
    body = "\n".join(f"{inner}{n}={v}," for n, v in kw_args)
    return f"{cls_name}(\n{body}\n{pad})"


def _pydantic_kw_args(obj: BaseModel, indent: int) -> list[tuple[str, str]]:
    cls = type(obj)
    out: list[tuple[str, str]] = []
    for field_name, field_info in cls.model_fields.items():
        val = getattr(obj, field_name)
        if field_name == "type" and not field_info.is_required():
            continue
        default = field_info.default
        if default is not PydanticUndefined and val == default:
            continue
        out.append((field_name, _emit_value(val, indent + 1)))
    return out


def _dataclass_kw_args(obj: Any, indent: int) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for f in fields(obj):
        val = getattr(obj, f.name)
        if f.default is not MISSING and val == f.default:
            continue
        out.append((f.name, _emit_value(val, indent + 1)))
    return out


def _emit_model(obj: BaseModel, indent: int = 0) -> str:
    return _format_constructor(type(obj).__name__, _pydantic_kw_args(obj, indent), indent)


def _emit_dataclass(obj: Any, indent: int = 0) -> str:
    return _format_constructor(type(obj).__name__, _dataclass_kw_args(obj, indent), indent)


# ---------------------------------------------------------------------------
# Import block: walk values and import learning_commons_evaluators types used.
# ---------------------------------------------------------------------------


def _collect_lce_types(obj: Any, found: set[type]) -> None:
    if isinstance(obj, Enum):
        found.add(type(obj))
    elif is_dataclass(obj) and not isinstance(obj, type):
        found.add(type(obj))
        for f in fields(obj):
            _collect_lce_types(getattr(obj, f.name), found)
    elif isinstance(obj, BaseModel):
        found.add(type(obj))
        for field_name in type(obj).model_fields:
            _collect_lce_types(getattr(obj, field_name), found)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_lce_types(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _collect_lce_types(v, found)


def _build_import_block(
    config: EvaluatorSettingsResult,
    settings_cls: type[EvaluationSettings],
) -> str:
    found: set[type] = set()
    _collect_lce_types(config.evaluator_metadata, found)
    _collect_lce_types(config.evaluation_settings, found)
    _collect_lce_types(config.prompts, found)
    found.add(settings_cls)
    found.add(EvaluatorSettingsResult)

    prefix = f"{_LCE_PACKAGE}."
    by_module: dict[str, list[str]] = {}
    for cls in found:
        mod = cls.__module__
        if not mod.startswith(prefix):
            continue
        by_module.setdefault(mod, []).append(cls.__name__)

    lines: list[str] = []
    for mod in sorted(by_module):
        syms = sorted(set(by_module[mod]))
        if len(syms) == 1:
            lines.append(f"from {mod} import {syms[0]}")
        else:
            lines.append(f"from {mod} import {', '.join(syms)}")
    return "\n".join(lines)


_MODULE_TEMPLATE = Template(
    """# !! AUTO-GENERATED — do not edit directly.
# Source: $rel_toml
# Regenerate : python scripts/generate_settings.py
# Staleness check: python scripts/generate_settings.py --check

from __future__ import annotations

$imports

# ── Evaluator metadata ────────────────────────────────────────────────────────

_EVALUATOR_METADATA = $metadata_code

# ── Prompt templates ──────────────────────────────────────────────────────────

_PROMPTS: dict[str, str] = $prompts_code

# ── Evaluation settings ───────────────────────────────────────────────────────

_EVALUATION_SETTINGS = $settings_code

# ── Public config object (imported by evaluator modules) ──────────────────────

CONFIG: EvaluatorSettingsResult[$settings_cls_name] = EvaluatorSettingsResult(
    evaluator_metadata=_EVALUATOR_METADATA,
    evaluation_settings=_EVALUATION_SETTINGS,
    prompts=_PROMPTS,
)
"""
)


def generate_module(
    _evaluator_name: str,
    toml_path: Path,
    settings_cls: type[EvaluationSettings],
) -> str:
    """Parse *toml_path* and return the content of the generated Python module."""
    config = load_evaluator_settings(toml_path, settings_cls)
    settings_cls_name = settings_cls.__name__

    return _MODULE_TEMPLATE.substitute(
        rel_toml=str(toml_path.relative_to(_REPO_ROOT)),
        imports=_build_import_block(config, settings_cls),
        metadata_code=_emit_model(config.evaluator_metadata),
        prompts_code=_emit_value(config.prompts),
        settings_code=_emit_model(config.evaluation_settings),
        settings_cls_name=settings_cls_name,
    )


# ---------------------------------------------------------------------------
# Evaluator discovery
# ---------------------------------------------------------------------------


def _snake_to_pascal(name: str) -> str:
    return "".join(part.capitalize() for part in name.split("_"))


def _resolve_settings_class(evaluator_name: str) -> type[EvaluationSettings]:
    """Import ``<Pascal>EvaluationSettings`` from ``learning_commons_evaluators.schemas.<name>``."""
    py_name = evaluator_name.replace("-", "_")
    if not py_name.isidentifier():
        raise SystemExit(
            f"Evaluator folder name {evaluator_name!r} is not a valid Python identifier "
            "(after converting hyphens to underscores); rename the directory under sdks/settings/."
        )
    class_name = f"{_snake_to_pascal(py_name)}EvaluationSettings"
    module_name = f"{_LCE_PACKAGE}.schemas.{py_name}"
    try:
        mod = importlib.import_module(module_name)
    except ModuleNotFoundError as e:
        raise SystemExit(
            f"No Python module {module_name!r} for evaluator {evaluator_name!r} "
            f"(expected class {class_name}). Add schemas/{py_name}.py or align the folder name."
        ) from e
    try:
        cls = getattr(mod, class_name)
    except AttributeError as e:
        raise SystemExit(
            f"Module {module_name!r} has no attribute {class_name!r}. "
            f"Define {class_name} there (subclass of EvaluationSettings), or align names."
        ) from e
    if not isinstance(cls, type) or not issubclass(cls, EvaluationSettings):
        raise SystemExit(f"{module_name}.{class_name} must be a subclass of EvaluationSettings.")
    return cls


@dataclass(frozen=True)
class _EvaluatorTarget:
    """One evaluator with a canonical TOML and its generated module path."""

    name: str
    settings_cls: type[EvaluationSettings]
    toml_path: Path
    output_path: Path


def _discover_evaluators() -> list[_EvaluatorTarget]:
    if not _SETTINGS_DIR.is_dir():
        return []
    out: list[_EvaluatorTarget] = []
    for child in sorted(_SETTINGS_DIR.iterdir()):
        if not child.is_dir():
            continue
        toml_path = child / "settings.toml"
        if not toml_path.is_file():
            continue
        name = child.name
        settings_cls = _resolve_settings_class(name)
        output = _GENERATED_DIR / f"_generated_{name.replace('-', '_')}_settings.py"
        out.append(
            _EvaluatorTarget(
                name=name,
                settings_cls=settings_cls,
                toml_path=toml_path,
                output_path=output,
            )
        )
    return out


def _contracts_toml(evaluator_name: str) -> Path:
    return _SETTINGS_DIR / evaluator_name / "contracts.toml"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_generate() -> None:
    targets = _discover_evaluators()
    if not targets:
        print(f"No evaluators found under {_SETTINGS_DIR} (add */settings.toml).")
        return
    for t in targets:
        content = generate_module(t.name, t.toml_path, t.settings_cls)
        t.output_path.write_text(content, encoding="utf-8")
        print(f"  generated  {t.output_path.relative_to(_REPO_ROOT)}")
    print("Done.")


def cmd_check() -> int:
    targets = _discover_evaluators()
    if not targets:
        print(f"No evaluators found under {_SETTINGS_DIR} (nothing to check).")
        return 0
    stale: list[str] = []
    for t in targets:
        expected = generate_module(t.name, t.toml_path, t.settings_cls)
        actual = t.output_path.read_text(encoding="utf-8") if t.output_path.exists() else ""
        if expected != actual:
            diff = "".join(
                difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=str(t.output_path.relative_to(_REPO_ROOT)),
                    tofile="(regenerated)",
                    n=3,
                )
            )
            print(f"STALE: {t.output_path.relative_to(_REPO_ROOT)}\n{diff}")
            stale.append(t.name)

    if stale:
        print(f"\nStale evaluators: {stale}")
        print("Run:  python scripts/generate_settings.py")
        return 1

    print("All generated settings are up to date.")
    return 0


def cmd_sync() -> None:
    targets = _discover_evaluators()
    if not targets:
        print(f"No evaluators found under {_SETTINGS_DIR} (nothing to sync).")
        return
    for t in targets:
        src = _contracts_toml(t.name)
        if not src.exists():
            print(f"  WARNING: canonical {src.relative_to(_REPO_ROOT)} not found — skipping")
            continue
        dst_dir = _GENERATED_DIR / t.name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / "contracts.toml"
        dst.write_bytes(src.read_bytes())
        print(f"  copied   {src.relative_to(_REPO_ROOT)} → {dst.relative_to(_REPO_ROOT)}")
    print("Done.")


def cmd_check_sync() -> int:
    targets = _discover_evaluators()
    if not targets:
        print(f"No evaluators found under {_SETTINGS_DIR} (nothing to verify).")
        return 0
    errors: list[str] = []
    for t in targets:
        canonical = _contracts_toml(t.name)
        if not canonical.exists():
            print(f"  WARNING: canonical {canonical.relative_to(_REPO_ROOT)} not found — skipping")
            continue
        bundled = _GENERATED_DIR / t.name / "contracts.toml"
        if not bundled.exists():
            errors.append(
                f"MISSING bundled: {bundled.relative_to(_REPO_ROOT)} "
                f"(run: python scripts/generate_settings.py --sync)"
            )
        elif canonical.read_bytes() != bundled.read_bytes():
            errors.append(
                f"OUT OF SYNC: {t.name}/contracts.toml "
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
