#!/usr/bin/env bash
# Rebuild GaussIQ API/UI Allure HTML under docs/reports/allure-gaussiq-*.
# Same pipeline as DataHub: pytest --alluredir, split by suite, allure generate --single-file.
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

SPLIT_ROOT="${TMPDIR:-/tmp}/allure-gaussiq-split"
API_RESULTS="${TMPDIR:-/tmp}/gaussiq-allure-api"
UI_RESULTS="${TMPDIR:-/tmp}/gaussiq-allure-ui"
rm -rf "$API_RESULTS" "$UI_RESULTS" "$SPLIT_ROOT"
mkdir -p "$API_RESULTS" "$UI_RESULTS"

set +e
python3 -m pytest tests/gaussiq_suites --alluredir="$API_RESULTS"
api_rc=$?
set -e
if [[ "$api_rc" -ne 0 && "$api_rc" -ne 1 ]]; then
  exit "$api_rc"
fi

python3 scripts/split_allure_by_suite.py "$API_RESULTS" "$SPLIT_ROOT/api"
for suite in smoke sanity regression product; do
  run_allure generate "$SPLIT_ROOT/api/$suite" -o "docs/reports/allure-gaussiq-api-${suite}" --clean --single-file --name "GaussIQ API ${suite}"
done

set +e
python3 -m pytest tests/gaussiq_ui --alluredir="$UI_RESULTS"
ui_rc=$?
set -e
if [[ "$ui_rc" -ne 0 && "$ui_rc" -ne 1 ]]; then
  exit "$ui_rc"
fi

python3 scripts/split_allure_by_suite.py "$UI_RESULTS" "$SPLIT_ROOT/ui"
for suite in smoke sanity regression; do
  run_allure generate "$SPLIT_ROOT/ui/$suite" -o "docs/reports/allure-gaussiq-ui-${suite}" --clean --single-file --name "GaussIQ UI ${suite}"
done

# Drop leftover homemade tables from the previous catalog-HTML experiment.
for leftover in docs/reports/allure-gaussiq-security-* docs/reports/allure-gaussiq-performance-*; do
  rm -rf "$leftover"
done

echo "Wrote docs/reports/allure-gaussiq-api-{smoke,sanity,regression,product} and allure-gaussiq-ui-{smoke,sanity,regression}"
