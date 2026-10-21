# UI agent skills

Canonical skill file: `.cursor/skills/ui-automation/SKILL.md`. How the lab console maps English to these suites: `AI-AGENT.md`.

## What this can do

- Drive `docs/` (GitHub Pages) with Playwright through page objects in `pages/`.
- Run `pytest -m smoke`, `pytest -m sanity`, or `pytest -m ui` from this folder.
- Map console English to the suite catalog: "Check UI sanity" → `handler:run_suite` with `layer=ui`. The in-browser console replays fixtures; this tree runs the browser.

## What this must not do

- Invent credentials. Lab login is fictional `emuser` / `empass` only.
- Call a model to decide pass/fail or to invent a selector.
- Mix API payload folders into UI reports.
