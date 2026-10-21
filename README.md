# Sanket Dhamke — DataHub ops / quality lab

Public portfolio sample: a **keyword/rule intent router** plus **pytest API automation** (and a short Playwright suite) around a fictional [DataHub](https://datahubproject.io) demo tenant.

This is an original sample of that architecture. It is **not affiliated with any prior employer product**. Charts, asset counts, and ingest runs are simulated. There is no live cluster.

Site (GitHub Pages, after publish): https://sanket-dhamke.github.io/sanket-qa-portfolio/

## What you can open

- [Home](docs/index.html) — Lead SDET; Hybrid AI Agent for performance testing; three cards. No city in the copy.
- [Lab console](docs/console.html) — Connect / Apply first (dummy cluster + AWS fields, memory-only). Then Hybrid AI Agent for performance testing: source **kind** chips, CPU/memory as **% of pod limit**, Tools, suites, rule RCA, Email report tab (simulated preview to `sanket.dhamke@gmail.com`, no SMTP).
- [Architecture](docs/architecture.html) — keyword/hybrid router, handlers, KB, suite catalog, rule RCA. A model does not choose tools, collect metrics, or set RCA.
- [API automation](docs/api-framework.html) — pytest + requests, smoke/sanity/regression tree under `tests/api/`. [Allure report](docs/reports/allure-api/index.html).
- [UI automation](docs/ui-framework.html) — Playwright + pytest page objects in `ui/`. [Allure report](docs/reports/allure-ui/index.html).

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m agent.export_web
pytest -p no:playwright tests/test_routing.py tests/test_hybrid_agent.py tests/test_rca_engine.py tests/test_layout.py tests/api
# Allure HTML (needs the Allure CLI):
# scripts/generate_allure.sh
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
cd ui
pip install -r requirements.txt
playwright install chromium
pytest -m ui
```

## Honesty

The router is keyword-based, not an LLM. Handlers read `agent/fixtures/`. Suites on GitHub Pages replay `agent/fixtures/suites.json` (same smoke/sanity/regression markers as pytest). Lab login is fictional `emuser` / `empass`. Python + `tests/test_routing.py` / `tests/test_hybrid_agent.py` are the source of truth.
