# UI automation (Playwright + pytest)

Separate from the API tree. Page objects in `pages/`. Tests in `tests/ui/`.

```bash
cd ui
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
pytest -m smoke
pytest -m sanity
pytest -m ui --alluredir=reports/allure-results
allure generate reports/allure-results -o ../docs/reports/allure-ui --clean --single-file --name "UI automation"
```

See `AI-AGENT.md` for how the Hybrid AI Agent for performance testing maps English to these suites.
