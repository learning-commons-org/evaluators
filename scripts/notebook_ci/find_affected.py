#!/usr/bin/env python3
"""Find which evaluator notebooks are affected by a set of changed files.

An evaluator is "affected" if any file in its declared dependency closure
changed -- not just the notebook itself. The closure is read straight out of
each evaluator's own config.json (no hand-maintained map to drift):
  - config.json itself
  - every prompt.messages[*].source_path (resolved relative to config.json's
    directory -- this also picks up cross-directory shares like Vocabulary's
    ../background-knowledge.txt)
  - input_schema / output_schema $ref targets
  - fixtures.path

The notebook to run is found in one of three places, checked in order:
  1. Co-located with config.json.
  2. One directory up, for evaluators that share one notebook across sibling
     configs (e.g. Vocabulary's grades-3-4/ and other-grades/ both point at
     the shared example_notebook.ipynb one level up).
  3. Climbing all the way to evals/, matching by name: a legacy notebook like
     evals/purpose_evaluator.ipynb for evals/prompts/purpose/config.json,
     matched because "purpose" (the config's own directory name) appears in
     the notebook's filename. Needed because not every evaluator has been
     migrated onto the co-located-notebook convention yet.

Usage:
    python3 scripts/notebook_ci/find_affected.py --changed-files-from FILE
    python3 scripts/notebook_ci/find_affected.py --changed-files a.txt b.py

Prints a JSON array of affected notebook paths (deduplicated) to stdout.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys


def tracked_files(pattern: str) -> list[str]:
    out = subprocess.check_output(["git", "ls-files", pattern], text=True)
    return [p for p in out.splitlines() if ".ipynb_checkpoints" not in p]


def evaluator_configs() -> list[str]:
    return tracked_files("evals/**/config.json")


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_closure(cfg_path: str) -> set[str]:
    """Every file this config declares a dependency on, config.json included."""
    base = os.path.dirname(cfg_path)
    closure = {cfg_path}

    try:
        config = load_json(cfg_path)
    except (OSError, json.JSONDecodeError):
        # An unreadable config can't declare a closure; eval-config will
        # already fail on this separately. Treat it as just itself.
        return closure

    for key in ("input_schema", "output_schema"):
        ref = config.get(key, {})
        if isinstance(ref, dict) and "$ref" in ref:
            closure.add(os.path.normpath(os.path.join(base, ref["$ref"])))

    for step in config.get("steps", []):
        for msg in step.get("prompt", {}).get("messages", []):
            src = msg.get("source_path")
            if src:
                closure.add(os.path.normpath(os.path.join(base, src)))

    fixtures_path = config.get("fixtures", {}).get("path")
    if fixtures_path:
        closure.add(os.path.normpath(os.path.join(base, fixtures_path)))

    return closure


def _name_key(name: str) -> str:
    """Normalize a directory or notebook stem for loose name matching:
    lowercase, strip a trailing _evaluator/-evaluator suffix, drop
    separators. "purpose" and "purpose_evaluator" both become "purpose"."""
    stem = re.sub(r"\.ipynb$", "", name, flags=re.IGNORECASE)
    stem = re.sub(r"[-_]?evaluator$", "", stem, flags=re.IGNORECASE)
    return re.sub(r"[-_]", "", stem).lower()


def notebook_for(cfg_path: str) -> str | None:
    """The notebook that exercises this config, checked in three tiers (see
    module docstring): co-located, one directory up, or name-matched while
    climbing to evals/."""
    base = os.path.dirname(cfg_path)

    own = tracked_files(os.path.join(base, "*.ipynb"))
    if own:
        return own[0]

    parent = os.path.dirname(base)
    shared = tracked_files(os.path.join(parent, "*.ipynb"))
    if shared:
        return shared[0]

    target_key = _name_key(os.path.basename(base))
    climb = parent
    while climb and climb.startswith("evals"):
        for candidate in tracked_files(os.path.join(climb, "*.ipynb")):
            if _name_key(os.path.basename(candidate)) == target_key:
                return candidate
        if climb == "evals":
            break
        climb = os.path.dirname(climb)

    return None


def find_affected(changed_files: set[str]) -> list[str]:
    # Callers may pass paths with "./" or ".." segments (or, off of git,
    # OS-specific separators); normalize so the intersection check below
    # matches config_closure()'s already-normalized entries.
    changed = {os.path.normpath(f) for f in changed_files}

    affected: dict[str, set[str]] = {}  # notebook path -> union of closures that hit it

    for cfg_path in evaluator_configs():
        notebook = notebook_for(cfg_path)
        if not notebook:
            continue  # config-only evaluator, nothing to execute

        closure = config_closure(cfg_path) | {notebook}
        if closure & changed:
            affected.setdefault(notebook, set()).update(closure)

    return sorted(affected.keys())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--changed-files-from",
        help="Path to a file with one changed path per line (e.g. from `git diff --name-only`).",
    )
    parser.add_argument(
        "--changed-files",
        nargs="*",
        default=[],
        help="Changed paths given directly on the command line.",
    )
    args = parser.parse_args()

    changed = set(args.changed_files)
    if args.changed_files_from:
        with open(args.changed_files_from, encoding="utf-8") as f:
            changed |= {line.strip() for line in f if line.strip()}

    if not changed:
        print("no changed files given", file=sys.stderr)

    print(json.dumps(find_affected(changed)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
