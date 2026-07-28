#!/usr/bin/env bash
# One-time local setup (run once per clone): install pre-commit + the harness
# deps and enable the repo check hooks so `python3 scripts/check.py --fix` runs
# before each commit.
set -euo pipefail

# Resolve repo root from this script's location so it works from any cwd.
cd "$(dirname "${BASH_SOURCE[0]}")/.."

# Invoke via `python3 -m` so it works even if pip installs to a dir not on PATH.
python3 -m pip install --quiet --upgrade pre-commit
python3 -m pip install --quiet -r scripts/requirements.txt
python3 -m pre_commit install

echo "✓ pre-commit hooks installed — repo checks will run on each commit."
echo "  Run manually anytime: python3 scripts/check.py --fix"
echo "  Bypass once if needed: git commit --no-verify (CI runs the same checks)"
