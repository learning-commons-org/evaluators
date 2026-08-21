"""Check registry. Add new checks here to wire them into the harness + CI."""

from .eval_config import EvalConfig
from .eval_fixtures import EvalFixtures
from .eval_model_constraints import EvalModelConstraints
from .eval_notebook import EvalNotebook
from .eval_requirements import EvalRequirements
from .eval_schemas import EvalSchemas
from .strip_notebooks import StripNotebooks

ALL_CHECKS = [
    StripNotebooks(),
    EvalConfig(),
    EvalSchemas(),
    EvalFixtures(),
    EvalNotebook(),
    EvalRequirements(),
    EvalModelConstraints(),
]
