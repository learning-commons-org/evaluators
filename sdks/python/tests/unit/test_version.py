"""``__version__``, including the branch that runs when package metadata is absent.

That fallback is the one line a release bump touches, and until now nothing executed it:
the suite always runs against an installed package, so ``importlib.metadata`` answers and
the ``except`` arm never does. The result was a release PR whose only Python change was an
uncovered line, failing the patch-coverage status for a version bump.
"""

from __future__ import annotations

import importlib
import importlib.metadata
import re
import tomllib
from pathlib import Path

import pytest

from learning_commons_evaluators import version as version_module

SDK_ROOT = Path(__file__).resolve().parents[2]

#: The literal in the ``except`` arm, read from source rather than by importing, so the
#: test sees what a reader sees even when metadata has already supplied something else.
FALLBACK = re.search(
    r'^\s+__version__ = "([^"]+)"', Path(version_module.__file__).read_text(), re.MULTILINE
)


def test_the_version_comes_from_package_metadata() -> None:
    assert version_module.__version__ == importlib.metadata.version("learning-commons-evaluators")


def test_the_fallback_is_used_when_the_package_has_no_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Running from a source tree that was never installed still reports a version.

    Telemetry stamps every event with it and the user agent carries it, so an import that
    raised here would take the whole package down over a missing ``.dist-info``.

    The restore is undone and reloaded by hand rather than left to a fixture. Fixture
    teardown runs in reverse order of setup, so a fixture reloading after ``monkeypatch``
    was requested would reload while the patch is *still* installed and leave every later
    test looking at a module frozen on the fallback — which happens to equal the real
    version today, so it would go unnoticed until the release where it does not.
    """

    def missing(_name: str) -> str:
        raise importlib.metadata.PackageNotFoundError("learning-commons-evaluators")

    monkeypatch.setattr(importlib.metadata, "version", missing)
    try:
        reloaded = importlib.reload(version_module)
        assert FALLBACK is not None
        assert reloaded.__version__ == FALLBACK.group(1)
    finally:
        monkeypatch.undo()
        importlib.reload(version_module)

    # The module is left as the rest of the suite expects to find it.
    assert version_module.__version__ == importlib.metadata.version("learning-commons-evaluators")


def test_the_fallback_matches_the_version_the_package_declares() -> None:
    """A release bump has to move both, and release-please is configured to.

    Without this, the two drift the first time one is edited by hand, and the fallback
    silently reports a version the package has not been for several releases.
    """
    declared = tomllib.loads((SDK_ROOT / "pyproject.toml").read_text())["project"]["version"]
    assert FALLBACK is not None
    assert FALLBACK.group(1) == declared


def test_the_description_is_exported() -> None:
    assert version_module.__description__
