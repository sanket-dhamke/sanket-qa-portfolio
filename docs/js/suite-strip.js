(function () {
  const el = document.querySelector("[data-testid=suite-strip]");
  if (!el) return;
  const layer = el.getAttribute("data-layer");
  fetch("js/suite-results.json")
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (!data || !data[layer]) return;
      ["smoke", "sanity", "regression"].forEach((suite) => {
        const row = data[layer][suite];
        const card = el.querySelector('[data-suite="' + suite + '"]');
        if (!card || !row) return;
        const count = card.querySelector("[data-count]");
        if (count) count.textContent = String(row.tests);
        const verdict = card.querySelector("[data-verdict]");
        if (verdict) {
          verdict.textContent = row.verdict;
          verdict.className = "verdict " + (row.verdict === "PASS" ? "pass" : "fail");
        }
        const why = card.querySelector("[data-why]");
        if (why) why.textContent = row.why || "";
      });
    })
    .catch(function () {
      /* baked HTML counts stay */
    });
})();
