# How the hybrid agent triggers UI suites

The public console is **keyword/rule** first. A model never chooses the tool and never invents a pass/fail.

| You say | Route | What runs |
|---|---|---|
| Check UI sanity | `handler:run_suite` | Replays `agent/fixtures/suites.json` cases with `suites: ["sanity"]` and `layer: ui` |
| Run smoke / sanity / regression | same | Marker catalog. GitHub Pages does not spawn Playwright; pytest in `ui/` does. |
| Current state of the application | `handler:app_status` | Smoke + sanity, then asks before full regression |

UI pytest (this folder) is the live check against `docs/`:

```bash
cd ui
pip install -r requirements.txt
playwright install chromium
pytest -m ui
```

Page objects live in `pages/`. Failures should print Symptom / Cause / Fix in the console agent when a catalog case fails (MAE OOMKilled makes UI search fail in the fixture).
