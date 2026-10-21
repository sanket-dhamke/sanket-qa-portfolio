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
pytest -m ui --html=reports/pytest-report.html --self-contained-html
```

See `AI-AGENT.md` for how the hybrid lab agent maps English to these suites.
