"""Check that an evaluator's example notebook reads from its config, not copies.

Where an evaluator ships a notebook alongside its config, the notebook should
load the canonical assets from disk (config.json + the prompt files declared in
it) rather than hardcoding prompts/schema inline — so the notebook can't drift
from the source of truth. Evaluators without a notebook (e.g. config-only ones)
are skipped.

This is a lightweight heuristic: it confirms the notebook's code references
config.json and loads the prompt files (by the `source_path` loader pattern, or
by naming each prompt file). It does not execute the notebook.
"""

from __future__ import annotations

import json
import os

from .base import Check, Result, Violation, evaluator_configs, load_json, tracked_files


class EvalNotebook(Check):
    name = "eval-notebook"
    description = "Where an evaluator ships a notebook, confirm it loads config + prompts from disk"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)
        for cfg_path in evaluator_configs():
            self._check_notebook(cfg_path, result)
        return result

    def _check_notebook(self, cfg_path: str, result: Result) -> None:
        base = os.path.dirname(cfg_path)
        # Git-tracked only, so local/untracked notebooks and checkpoints don't trip the check.
        notebooks = tracked_files(os.path.join(base, "*.ipynb"))
        if not notebooks:
            return  # config-only evaluator — nothing to check

        try:
            config = load_json(cfg_path)
        except (OSError, json.JSONDecodeError):
            return  # eval-config reports unreadable configs
        prompt_files = [
            m["source_path"]
            for m in config.get("steps", [{}])[0].get("prompt", {}).get("messages", [])
            if m.get("source_path")
        ]

        for nb_path in notebooks:
            src = self._code_source(nb_path)
            if src is None:
                result.violations.append(Violation(nb_path, "invalid notebook JSON"))
                continue

            if "config.json" not in src:
                result.violations.append(
                    Violation(nb_path, "does not load config.json — should read the config, not hardcode it")
                )
            # Either the dynamic loader pattern, or every prompt file named explicitly.
            loads_prompts = "source_path" in src or (
                prompt_files and all(pf in src for pf in prompt_files)
            )
            if not loads_prompts:
                result.violations.append(
                    Violation(nb_path, "does not load the prompt files from disk (no source_path loader nor prompt filenames)")
                )

    @staticmethod
    def _code_source(nb_path: str) -> str | None:
        """Concatenated source of a notebook's code cells, or None if unreadable."""
        try:
            nb = load_json(nb_path)
        except (OSError, json.JSONDecodeError):
            return None
        return "\n".join(
            "".join(c.get("source", []))
            for c in nb.get("cells", [])
            if c.get("cell_type") == "code"
        )
