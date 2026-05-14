"""Smoke tests for package public API imports."""

import importlib


def test_root_package_public_api():
    """Every name in ``__all__`` is defined on the root package (single source of truth)."""
    pkg = importlib.import_module("learning_commons_evaluators")
    missing = [name for name in pkg.__all__ if not hasattr(pkg, name)]
    assert not missing, f"__all__ lists undefined names: {missing}"
    for name in pkg.__all__:
        assert getattr(pkg, name) is not None, name


def test_providers_public_api():
    """Every name in ``providers.__all__`` is defined on the submodule."""
    providers = importlib.import_module("learning_commons_evaluators.providers")
    missing = [name for name in providers.__all__ if not hasattr(providers, name)]
    assert not missing, f"providers.__all__ lists undefined names: {missing}"
    for name in providers.__all__:
        assert getattr(providers, name) is not None, name
