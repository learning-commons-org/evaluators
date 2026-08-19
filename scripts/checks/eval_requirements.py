"""Validate evals/requirements.txt against what evals/ actually imports.

Static only -- no network, no `pip install` -- so this runs in the same fast,
deterministic harness as every other check. Two directions:

1. Every non-stdlib, non-local import used across evals/**/*.ipynb and
   evals/**/*.py must be satisfied by a requirements.txt entry (or an
   explicit "transitively provided" exemption below). Catches genuinely
   missing dependencies before a fresh install breaks on them --
   `anthropic` and `requests` were both used by a notebook without being
   listed, found by exactly this scan.
2. Every requirements.txt entry expected to be imported directly (i.e. not
   Jupyter tooling) should actually show up somewhere in the scanned
   imports. Catches stale/dead dependencies.

Package-name -> import-name only needs an entry below when they differ;
this is a small, explicit map of what's actually in requirements.txt today,
not a generic guesser -- a wrong guess here should be a loud KeyError in
review, not a silent false pass.
"""

from __future__ import annotations

import ast
import json
import os
import re
import sys

from .base import Check, Result, Violation, tracked_files

REQUIREMENTS_PATH = "evals/requirements.txt"

# Tooling that a fresh `pip install` needs but eval code never imports
# directly (Jupyter itself, its execution engine, IDE language servers).
TOOLING_ONLY = {
    "jupyter",
    "nbconvert",
    "ipykernel",
    "python-language-server",
    "python-lsp-server",
}

# package name (as written in requirements.txt) -> the name it's imported
# under, when they differ.
IMPORT_NAME = {
    "python-dotenv": "dotenv",
    "langchain-google-genai": "langchain_google_genai",
    "langchain-openai": "langchain_openai",
}

# Imports that resolve without their own requirements.txt entry because a
# listed package pulls them in transitively, or because they're local to
# evals/ rather than a PyPI dependency.
TRANSITIVE_OR_LOCAL = {
    "langchain_core": "ships with langchain",
    "IPython": "ships with jupyter/ipykernel",
    "prompts": "local package under evals/prompts, not a PyPI dependency",
}


_NAME_RE = re.compile(r"^[A-Za-z0-9._-]+")


def _requirements() -> dict[str, str]:
    """package name -> import name, skipping comments/blank lines.

    Strips version specifiers/extras/markers (e.g. `pydantic>=2.0` ->
    `pydantic`) before mapping, so a pin doesn't produce a package name
    that can never match an import.
    """
    with open(REQUIREMENTS_PATH, encoding="utf-8") as f:
        raw = [
            line.strip()
            for line in f
            if line.strip() and not line.strip().startswith("#")
        ]
    names = [m.group(0) for line in raw if (m := _NAME_RE.match(line))]
    return {name: IMPORT_NAME.get(name, name.replace("-", "_")) for name in names}


def _top_level_imports(source: str) -> set[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module.split(".")[0])
    return names


def _tracked_evals_files(suffix: str) -> set[str]:
    """`evals/**/*<suffix>` misses files directly in evals/ -- git's glob
    pathspec requires `**` to span at least one directory. Union with the
    top-level pattern so `evals/*.py` files aren't silently skipped."""
    return set(tracked_files(f"evals/*{suffix}")) | set(tracked_files(f"evals/**/*{suffix}"))


def _scan_evals_imports() -> set[str]:
    found = set()

    for path in sorted(_tracked_evals_files(".py")):
        with open(path, encoding="utf-8") as f:
            found |= _top_level_imports(f.read())

    for path in sorted(_tracked_evals_files(".ipynb")):
        try:
            with open(path, encoding="utf-8") as f:
                nb = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        for cell in nb.get("cells", []):
            if cell.get("cell_type") != "code":
                continue
            src = "".join(cell.get("source", []))
            src = re.sub(r"^\s*%.*$", "", src, flags=re.M)  # strip magics (%pip, ...)
            found |= _top_level_imports(src)

    return found


class EvalRequirements(Check):
    name = "eval-requirements"
    description = "Cross-check evals/requirements.txt against imports actually used in evals/"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)

        if not os.path.exists(REQUIREMENTS_PATH):
            result.violations.append(Violation(REQUIREMENTS_PATH, "file not found"))
            return result

        requirements = _requirements()
        used_imports = _scan_evals_imports()
        stdlib = sys.stdlib_module_names

        # Direction 1: imported in evals/, but no requirements.txt entry covers it.
        declared_imports = set(requirements.values())
        for name in sorted(used_imports):
            if name in stdlib or name in TRANSITIVE_OR_LOCAL or name in declared_imports:
                continue
            result.violations.append(
                Violation(
                    REQUIREMENTS_PATH,
                    f"`{name}` is imported somewhere in evals/ but has no requirements.txt "
                    f"entry (and isn't in TRANSITIVE_OR_LOCAL) -- add it, or add the "
                    f"exemption with a reason if it's genuinely transitive",
                )
            )

        # Direction 2: listed in requirements.txt, expected to be imported, never is.
        for package, import_name in sorted(requirements.items()):
            if package in TOOLING_ONLY:
                continue
            if import_name not in used_imports:
                result.violations.append(
                    Violation(
                        REQUIREMENTS_PATH,
                        f"`{package}` is listed but never imported anywhere in evals/ "
                        f"-- looks stale, or needs a TOOLING_ONLY / IMPORT_NAME entry if "
                        f"this scan is wrong about it",
                    )
                )

        return result
