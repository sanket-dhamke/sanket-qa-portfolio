# Sanket Dhamke — DataHub ops / quality lab

Public portfolio sample: a **keyword/rule intent router** plus **pytest API automation** (and a short Playwright suite) around a fictional [DataHub](https://datahubproject.io) demo tenant.

This is an original sample of that architecture. It is **not affiliated with any prior employer product**. Charts, asset counts, and ingest runs are simulated. There is no live cluster.

Site (GitHub Pages, after publish): https://sanket-dhamke.github.io/sanket-qa-portfolio/

## What you can open

- [Home](docs/index.html) — Lead SDET; hybrid agentic QA; three cards. No city in the copy.
- [Lab console](docs/console.html) — hybrid agent: source **kind** chips (handler vs knowledge base vs suite), CPU/memory as **% of pod limit**, Tools catalog, suites, rule RCA (fired + skipped), login API, incidents, capacity for 1M/10M assets, postgres recipe YAML → simulated GraphQL ingest.
- [Architecture](docs/architecture.html) — router, handlers, KB, suite catalog, rule RCA. A model does not choose tools, collect metrics, or set RCA.
- [API framework](docs/api-framework.html) — folder map, pytest, sample HTML report.

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m agent.export_web
pytest tests/test_routing.py tests/test_hybrid_agent.py tests/test_rca_engine.py tests/api \
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

The router is keyword-based, not an LLM. Handlers read `agent/fixtures/`. Suites on GitHub Pages replay `agent/fixtures/suites.json` (same smoke/sanity/regression markers as pytest). Lab login is fictional `emuser` / `empass`. Python + `tests/test_routing.py` / `tests/test_hybrid_agent.py` are the source of truth.
