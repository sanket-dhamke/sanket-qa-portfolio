---
name: ui-automation
description: >
  Run Playwright + pytest UI suites for the public DataHub ops lab.
  Use when the user asks for UI sanity, UI smoke, page-object tests,
  or how the hybrid agent triggers UI suites.
---

# UI automation agent

## What this can do

- Drive `docs/` (GitHub Pages) with Playwright through page objects in `ui/pages/`.
- Run `pytest -c ui/pytest.ini -m ui` (or smoke/sanity/regression markers).
- Map console English to the suite catalog: "Check UI sanity" → `handler:run_suite` with `layer=ui`. The in-browser console **replays fixtures**; this skill runs the real browser tests.

## What this must not do

- Invent credentials. Lab login is fictional `emuser` / `empass` only.
- Call a model to decide pass/fail or to invent a selector.
- Mix API payload folders (`tests/payloads/`, mock GMS) into UI reports.

## Commands

```bash
cd ui
pip install -r requirements.txt
playwright install chromium
pytest -m smoke
pytest -m sanity
pytest -m ui
```

## Pages

| Page object | URL |
|---|---|
| `HomePage` | `index.html` |
| `ConsolePage` | `console.html` |
| `ArchitecturePage` | `architecture.html` |
| `ApiFrameworkPage` | `api-framework.html` (assert API page stays API-only) |
| `UiFrameworkPage` | `ui-framework.html` |
