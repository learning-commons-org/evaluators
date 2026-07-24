#!/usr/bin/env bash
# One-time local setup (run once per clone): install pre-commit and enable the
# repo check hooks so `python scripts/check.py --fix` runs before each commit.
set -euo pipefail

python3 -m pip install --quiet --upgrade pre-commit
pre-commit install

echo "✓ pre-commit hooks installed — repo checks will run on each commit."
echo "  Run manually anytime: python scripts/check.py --fix"
echo "  Bypass once if needed: git commit --no-verify (CI runs the same checks)"
