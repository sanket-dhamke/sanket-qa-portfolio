# Sanket Dhamke — DataHub ops / quality lab

Public portfolio sample: a **keyword/rule intent router** plus **pytest API automation** (and a short Playwright suite) around a fictional [DataHub](https://datahubproject.io) demo tenant.

This is an original sample of that architecture. It is **not affiliated with any prior employer product**. Charts, asset counts, and ingest runs are simulated. There is no live cluster.

Site (GitHub Pages, after publish): https://sanket-dhamke.github.io/sanket-qa-portfolio/

## What you can open

- [Home](docs/index.html) — who I am (Lead SDET, 12 years, Pune) and three cards.
- [Lab console](docs/console.html) — chat with a visible `source` chip, live CPU/memory charts, pod health, RCA, postgres recipe YAML → simulated `createIngestionSource` + `createIngestionExecutionRequest`.
- [Architecture](docs/architecture.html) — router, handlers, KB, “model never produces a number”.
- [API framework](docs/api-framework.html) — folder map, pytest, sample HTML report.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m agent.export_web
pytest tests/test_routing.py tests/api \
  --html=docs/reports/pytest-report.html --self-contained-html
python -m http.server 8765 --directory docs
# open http://127.0.0.1:8765/
```

CLI router:

```bash
python -m agent "Show CPU and memory of datahub-gms"
```

Mock GMS (optional):

```bash
uvicorn api.app:app --port 8080
```

Playwright (optional, UI automation against this site):

```bash
playwright install chromium
pytest -m ui tests/ui
```

## Honesty

The router is keyword-based, not an LLM. Handlers read `agent/fixtures/`. The in-browser demo is a JS port of the Python router so GitHub Pages works without Python. Python + `tests/test_routing.py` are the source of truth.
