"""Evaluator settings package — TOML configs and contract test data.

This package is the authoritative source for evaluator settings when the SDK is
installed via pip.  When working inside the monorepo the shared copy at
``sdks/settings/`` is used instead (controlled by ``EVALUATORS_SETTINGS_DIR``).

See :func:`~learning_commons_evaluators.settings.load_settings.shared_settings_root`
for the resolution order.
"""
