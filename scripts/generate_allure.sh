#!/usr/bin/env bash
# Rebuild the static Allure HTML committed under docs/reports/.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

run_allure() {
  if [[ -n "${ALLURE_BIN:-}" ]]; then
    "$ALLURE_BIN" "$@"
  elif command -v allure >/dev/null 2>&1; then
    allure "$@"
  else
    npx --yes allure-commandline "$@"
  fi
}

python3 scripts/write_suites_catalog.py
python3 -m agent.export_web
python3 scripts/write_suite_results.py

mkdir -p reports/allure-results ui/reports/allure-results
find reports/allure-results ui/reports/allure-results -type f ! -name '.gitkeep' -delete

set +e
python3 -m pytest -p no:playwright tests/api --alluredir=reports/allure-results
api_rc=$?
( cd ui && python3 -m pytest -m ui --alluredir=reports/allure-results )
ui_rc=$?
set -e
# 0 = green, 1 = expected lab_issue failures (mae-consumer OOM). Anything else is a runner error.
for rc in "$api_rc" "$ui_rc"; do
  if [[ "$rc" -ne 0 && "$rc" -ne 1 ]]; then
    exit "$rc"
  fi
done
run_allure generate reports/allure-results -o docs/reports/allure-api --clean --single-file --name "API automation"
run_allure generate ui/reports/allure-results -o docs/reports/allure-ui --clean --single-file --name "UI automation"

SPLIT_ROOT="${TMPDIR:-/tmp}/allure-suite-split"
python3 scripts/split_allure_by_suite.py reports/allure-results "$SPLIT_ROOT/api"
python3 scripts/split_allure_by_suite.py ui/reports/allure-results "$SPLIT_ROOT/ui"
for suite in smoke sanity regression; do
  run_allure generate "$SPLIT_ROOT/api/$suite" -o "docs/reports/allure-api-${suite}" --clean --single-file --name "API ${suite}"
  run_allure generate "$SPLIT_ROOT/ui/$suite" -o "docs/reports/allure-ui-${suite}" --clean --single-file --name "UI ${suite}"
done

echo "Wrote docs/reports/allure-api, allure-ui, and per-suite smoke/sanity/regression slices"
