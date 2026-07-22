"""Check registry. Add new checks here to wire them into the harness + CI."""

from .eval_config import EvalConfig
from .strip_notebooks import StripNotebooks

ALL_CHECKS = [
    StripNotebooks(),
    EvalConfig(),
]
