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

mkdir -p reports/allure-results ui/reports/allure-results
find reports/allure-results ui/reports/allure-results -type f ! -name '.gitkeep' -delete

python3 -m pytest -p no:playwright tests/api --alluredir=reports/allure-results
run_allure generate reports/allure-results -o docs/reports/allure-api --clean --single-file --name "API automation"

( cd ui && python3 -m pytest -m ui --alluredir=reports/allure-results )
run_allure generate ui/reports/allure-results -o docs/reports/allure-ui --clean --single-file --name "UI automation"

echo "Wrote docs/reports/allure-api and docs/reports/allure-ui"
