"""Check registry. Add new checks here to wire them into the harness + CI."""

from .eval_configs import EvalConfigs
from .strip_notebooks import StripNotebooks

ALL_CHECKS = [
    StripNotebooks(),
    EvalConfigs(),
]
