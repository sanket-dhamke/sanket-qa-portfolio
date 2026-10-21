# API reports

Raw Allure results:

```bash
pytest tests/api --alluredir=reports/allure-results
allure generate reports/allure-results -o docs/reports/allure-api --clean --single-file --name "API automation"
```

`reports/allure-results/` holds the JSON Allure writes. Generated files are gitignored; `.gitkeep` keeps the folder. The GitHub Pages Allure site is `docs/reports/allure-api/`.

Or run `scripts/generate_allure.sh` (API + UI).
