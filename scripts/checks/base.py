"""Shared contract for repo checks.

Every check is a `Check` subclass that implements `run(fix)` and returns a
`Result`. A check must, in one pass:
  - report *every* violation it finds (no stop-at-first), and
  - in fix mode, repair what it safely can and report what's left.
"""

from __future__ import annotations

import json
import os
import subprocess
from dataclasses import dataclass, field

# Shared, version-pinned schemas live here (not duplicated per evaluator).
SCHEMA_ROOT = "evals/_schemas"


@dataclass
class Violation:
    path: str
    message: str
    line: int | None = None

    def render(self) -> str:
        loc = self.path if self.line is None else f"{self.path}:{self.line}"
        return f"{loc} — {self.message}"


@dataclass
class Result:
    check: str
    violations: list[Violation] = field(default_factory=list)
    fixed: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.violations


class Check:
    """Base class. `name` is the CLI selector; `description` shows in --list."""

    name: str = ""
    description: str = ""

    def run(self, fix: bool) -> Result:  # pragma: no cover - interface
        raise NotImplementedError


def tracked_files(pattern: str) -> list[str]:
    """Git-tracked paths matching `pattern`, excluding checkpoint dirs."""
    out = subprocess.check_output(["git", "ls-files", pattern], text=True)
    return [p for p in out.splitlines() if ".ipynb_checkpoints" not in p]


def evaluator_configs() -> list[str]:
    """Every evaluator's config.json (an evaluator = a dir under evals/ with one)."""
    return tracked_files("evals/**/config.json")


def shared_schema_path(spec_version: str, name: str) -> str:
    """Path to a version-pinned shared schema, e.g. evals/_schemas/1.0/<name>."""
    return os.path.join(SCHEMA_ROOT, spec_version, name)


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
