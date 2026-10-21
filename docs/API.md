# API automation (pytest + requests)

Mock DataHub GMS only (`api/app.py`). Fictional `emuser` / `empass`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-api.txt
# optional live mock:
# uvicorn api.app:app --port 8080
pytest -m smoke tests/api
pytest -m sanity tests/api
pytest -m regression tests/api
pytest tests/api --alluredir=reports/allure-results
allure generate reports/allure-results -o docs/reports/allure-api --clean --single-file --name "API automation"
pytest tests/api --run-live -m live
```

Markers live in root `pytest.ini`. Payloads are JSON/YAML under `tests/payloads/`. Helpers under `tests/helpers/` build GraphQL bodies. `utils/gms.py` is the `requests` client for a running mock. `config/settings.py` reads `GMS_BASE_URL` / lab user from the environment.

Allure needs the CLI (`allure` on PATH, or `npx --yes allure-commandline`). `scripts/generate_allure.sh` rebuilds this HTML.
