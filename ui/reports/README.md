# UI reports

Raw Allure results for Playwright + pytest:

```bash
cd ui
pytest -m ui --alluredir=reports/allure-results
allure generate reports/allure-results -o ../docs/reports/allure-ui --clean --single-file --name "UI automation"
```

`allure-results/` is gitignored except `.gitkeep`. The GitHub Pages Allure site is `docs/reports/allure-ui/`.
