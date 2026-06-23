"""Entry point registry — imported by Inspect via the inspect_ai setuptools entry point.

Importing this module registers all scorers with Inspect's component system,
making them accessible by name (e.g. learning_commons_inspect_scorers/gla_scorer)
from both the Python API and the CLI.
"""

from learning_commons_inspect_scorers.gla import (
    gla_scorer,  # noqa: F401 — import triggers @scorer registry side-effect
)
