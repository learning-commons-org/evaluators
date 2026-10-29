#!/usr/bin/env bash
# One entry point for every QA script, in either SDK.
#
#   ./run.sh py|ts <input.json> [--spy-telemetry|--no-telemetry]   one evaluation (paid)
#   ./run.sh py|ts validate                                       D5, 22 cases (free)
#   ./run.sh py|ts errors                                         D6 config/provider errors (free)
#   ./run.sh py|ts async <input.json>                             D7, three concurrent calls (paid)
#   ./run.sh fixtures                                             write the eval's fixtures to inputs/fixtures/
#   ./run.sh --no-env ...                                         any of the above, ignoring both .env files
#
# Keys: export ANTHROPIC_API_KEY in your shell, or put it in a .env file here or at the
# repo root. The shell wins over qa/critical-thinking/.env, which wins over the root .env.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"

usage() { sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 2; }
abs() { (cd "$(dirname "$1")" && printf '%s/%s\n' "$(pwd)" "$(basename "$1")"); }

# Export KEY=VALUE lines from a .env file without overriding anything already set. The file
# is parsed, not sourced, so nothing in it runs. Empty values are skipped so a blank
# placeholder never hides a key from a later file.
load_env() {
  local file=$1 line key value loaded=()
  local assign='^[[:space:]]*(export[[:space:]]+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$'
  local dquoted='^"(.*)"$' squoted="^'(.*)'$"
  [[ -f $file ]] || return 0
  while IFS= read -r line || [[ -n $line ]]; do
    line=${line%$'\r'}
    [[ $line =~ $assign ]] || continue
    key=${BASH_REMATCH[2]}
    value=${BASH_REMATCH[3]}
    if [[ $value =~ $dquoted || $value =~ $squoted ]]; then
      value=${BASH_REMATCH[1]}
    else
      value=${value%%[[:space:]]#*}
    fi
    if [[ -n $value && -z ${!key:-} ]]; then
      export "$key=$value"
      loaded+=("$key")
    fi
  done <"$file"
  if [[ ${#loaded[@]} -gt 0 ]]; then
    echo "(loaded ${loaded[*]} from ${file#"$ROOT"/})" >&2
  fi
}

if [[ ${1:-} == --no-env ]]; then
  shift
  echo "(--no-env: ignoring .env files; only keys exported in this shell are used)" >&2
else
  load_env "$HERE/.env"
  load_env "$ROOT/.env"
fi

[[ $# -ge 1 ]] || usage

if [[ $1 == fixtures ]]; then
  mkdir -p "$HERE/inputs/fixtures"
  python3 - "$ROOT/evals/durable-skills/ela-writing/critical-thinking/fixtures.json" "$HERE/inputs/fixtures" <<'EOF'
import json, sys
for case in json.load(open(sys.argv[1], encoding="utf-8")):
    path = f"{sys.argv[2]}/{case['id']}.json"
    data = {"_note": f"Fixture {case['id']}; expert label {case['expected']['critical_thinking_score']} (adjacent level passes)."}
    data.update(case["input"])
    json.dump(data, open(path, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("wrote", path)
EOF
  exit 0
fi

sdk=$1; shift
[[ $sdk == py || $sdk == ts ]] || usage
[[ $# -ge 1 ]] || usage

case "$1" in
  validate) cmd=validate; set -- "$HERE/inputs/validation_cases.json" ;;
  errors)   cmd=errors; shift ;;
  async)    cmd=async; shift; [[ $# -ge 1 ]] || usage; set -- "$(abs "$1")" "${@:2}" ;;
  *)        cmd=run; set -- "$(abs "$1")" "${@:2}" ;;
esac

if [[ $sdk == py ]]; then
  [[ -x "$HERE/.venv/bin/python" ]] || { echo "Run ./setup.sh first." >&2; exit 1; }
  script=$(case $cmd in run) echo run_ct.py;; validate) echo check_validation.py;; errors) echo config_errors.py;; async) echo async_check.py;; esac)
  exec "$HERE/.venv/bin/python" "$HERE/python/$script" "$@"
else
  [[ -d "$HERE/ts/node_modules/@learning-commons/evaluators" ]] || { echo "Run ./setup.sh first." >&2; exit 1; }
  script=$(case $cmd in run) echo run-ct.ts;; validate) echo check-validation.ts;; errors) echo config-errors.ts;; async) echo async-check.ts;; esac)
  cd "$HERE/ts" && exec npx --no-install tsx "$script" "$@"
fi
