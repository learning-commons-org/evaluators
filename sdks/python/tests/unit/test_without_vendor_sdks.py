"""The package without its vendor SDKs, as an install with no extras will have it.

The check runs in a child process that hides the SDKs before anything imports them, so
it holds whether or not they are installed here; CI also runs it where they are not.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: Makes every vendor module unimportable, as if it were not installed, then runs the check.
SCRIPT = """
import sys

from tests.unit.without_vendor_sdks import is_vendor


class NotInstalled:
    def find_spec(self, name, path=None, target=None):
        if is_vendor(name):
            raise ModuleNotFoundError(f"No module named {name!r}", name=name)
        return None


sys.meta_path.insert(0, NotInstalled())

from tests.unit.without_vendor_sdks import main

main()
"""


def test_every_evaluator_runs_on_an_injected_provider_and_refuses_without_one() -> None:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT], cwd=ROOT, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr
