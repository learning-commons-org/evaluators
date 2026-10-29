#!/usr/bin/env bash
# Build and install both SDKs from this checkout, the way a user would receive them.
#
#   ./setup.sh            # both SDKs
#   ./setup.sh --python   # Python only (enough for the content track)
#   ./setup.sh --ts       # TypeScript only
#
# Python: a regular (non-editable) install of sdks/python, so pip builds a real package and
#         bundles the contracts and prompts the way the published wheel will.
# TypeScript: builds dist/, packs the package exactly as `npm publish` would, and installs that
#         tarball into ts/ with fresh peer dependencies, as an integrator's project would.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
DO_PY=1
DO_TS=1
case "${1:-}" in
  --python) DO_TS=0 ;;
  --ts) DO_PY=0 ;;
  "") ;;
  *) echo "Usage: ./setup.sh [--python|--ts]" >&2; exit 2 ;;
esac

step() { printf '\n==> %s\n' "$*"; }

if [[ $DO_PY == 1 ]]; then
  step "Python: checking version (needs 3.11+)"
  python3 -c 'import sys; assert sys.version_info >= (3, 11), sys.version' \
    || { echo "Python 3.11+ is required." >&2; exit 1; }

  step "Python: creating .venv and installing sdks/python (non-editable)"
  python3 -m venv "$HERE/.venv"
  "$HERE/.venv/bin/pip" install --quiet --upgrade pip
  "$HERE/.venv/bin/pip" install --quiet --force-reinstall --no-cache-dir "$ROOT/sdks/python"

  step "Python: checking the installed build has Critical Thinking"
  (cd "$HERE" && .venv/bin/python -c \
    "from learning_commons_evaluators import CriticalThinkingEvaluator; print('ok:', CriticalThinkingEvaluator.metadata.id)")
fi

if [[ $DO_TS == 1 ]]; then
  step "TypeScript: checking Node version (needs ^20.19 or >=22.12)"
  node -e '
    const [maj, min] = process.versions.node.split(".").map(Number);
    if (!((maj === 20 && min >= 19) || (maj === 22 && min >= 12) || maj > 22)) process.exit(1);
  ' || { echo "Node ^20.19.0 or >=22.12.0 is required (found $(node -v))." >&2; exit 1; }

  step "TypeScript: building and packing sdks/typescript"
  rm -f "$HERE"/ts/learning-commons-evaluators-*.tgz
  (cd "$ROOT/sdks/typescript" && npm ci --silent && npm run build --silent \
    && npm pack --silent --pack-destination "$HERE/ts")
  TGZ="$(cd "$HERE/ts" && ls learning-commons-evaluators-*.tgz | head -n 1)"

  step "TypeScript: installing $TGZ into ts/ with fresh peer dependencies"
  (cd "$HERE/ts" && npm install --silent \
    && npm install --silent --no-save "./$TGZ" "ai@>=7 <8" "zod@^4.1.8" "@ai-sdk/anthropic@>=4 <5")

  step "TypeScript: checking the installed build has Critical Thinking"
  (cd "$HERE/ts" && node --input-type=module -e \
    "import { CriticalThinkingEvaluator } from '@learning-commons/evaluators'; console.log('ok:', CriticalThinkingEvaluator.metadata.id)")
fi

step "Done. Built from commit $(git -C "$ROOT" rev-parse --short HEAD). Next:"
echo "    echo 'ANTHROPIC_API_KEY=<shared QA key>' > .env   # or export it in your shell"
echo "    ./run.sh py inputs/B-one-passage.json"
