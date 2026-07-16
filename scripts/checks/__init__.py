"""Check registry. Add new checks here to wire them into the harness + CI."""

from .strip_notebooks import StripNotebooks

ALL_CHECKS = [
    StripNotebooks(),
]
