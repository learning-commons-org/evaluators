"""Strip transient state from Jupyter notebooks, via nbstripout.

Drives nbstripout (pinned in scripts/requirements.txt) so we reuse its
battle-tested handling instead of reimplementing it. Flags chosen to match the
repo's intent:
  --keep-id        don't regenerate cell ids (avoids churn on otherwise-clean
                   notebooks)
  --extra-keys ... also strip the Databricks and Jupyter (outputs_hidden) cell
                   metadata that nbstripout keeps by default
nbstripout already clears outputs and execution counts. Notebook-level metadata
(kernelspec, language_info) is left intact.
"""

from __future__ import annotations

import shutil
import subprocess

from .base import Check, Result, Violation, tracked_files

# Cell metadata nbstripout does not strip by default but we want gone.
_EXTRA_KEYS = "cell.metadata.application/vnd.databricks.v1+cell cell.metadata.jupyter"
_FLAGS = ["--keep-id", "--extra-keys", _EXTRA_KEYS]


class StripNotebooks(Check):
    name = "strip-notebooks"
    description = "Clear outputs, execution counts, and cell metadata from notebooks (nbstripout)"

    def run(self, fix: bool) -> Result:
        result = Result(self.name)

        if shutil.which("nbstripout") is None:
            result.violations.append(
                Violation(
                    "scripts/requirements.txt",
                    "nbstripout not found; run `pip install -r scripts/requirements.txt`",
                )
            )
            return result

        for path in tracked_files("*.ipynb"):
            # --verify is a dry run: non-zero exit means the file would change.
            clean = subprocess.run(
                ["nbstripout", "--verify", *_FLAGS, path],
                capture_output=True,
            ).returncode == 0
            if clean:
                continue

            if fix:
                proc = subprocess.run(["nbstripout", *_FLAGS, path], capture_output=True, text=True)
                if proc.returncode == 0:
                    result.fixed.append(path)
                else:  # report and keep going, don't abort the whole pass
                    result.violations.append(
                        Violation(path, f"nbstripout failed: {proc.stderr.strip() or 'non-zero exit'}")
                    )
            else:
                result.violations.append(
                    Violation(path, "has outputs/execution counts/cell metadata; run with --fix")
                )
        return result
