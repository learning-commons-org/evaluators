"""Smoke tests for package public API imports."""


def test_main_package_imports():
    """All advertised public symbols can be imported from the root package."""
    from learning_commons_evaluators import (
        BaseEvaluator,
        ConventionalityEvaluator,
        __version__,
        create_config_no_telemetry,
    )

    assert __version__ is not None
    assert create_config_no_telemetry is not None
    assert ConventionalityEvaluator is not None
    assert BaseEvaluator is not None


def test_errors_import():
    from learning_commons_evaluators import (
        APIError,
        wrap_provider_error,
    )

    assert APIError is not None
    assert wrap_provider_error is not None


def test_providers_import():
    from learning_commons_evaluators.providers import (
        create_provider,
        token_usage_from_aimessage,
    )

    assert create_provider is not None
    assert token_usage_from_aimessage is not None
