(function () {
  const COLORS = {
    "case-intel-api": "#7eb0e4",
    "skills-intel-api": "#8fd6b8",
    "insights-api": "#c4a35a",
    "signal-connector": "#e05d4f",
    "rec-engine": "#c792ea",
  };

  const state = {
    data: null,
    session: { awaiting_regression: false },
    lastSuite: null,
    lastSmoke: null,
    lastSanity: null,
    connected: false,
  };

  const $ = (id) => document.getElementById(id);

  const PLAIN_CAUSE = {
    "CERT-MISMATCH": {
      title: "AJ18991 HTTP 500 is a certificate SAN mismatch",
      observation:
        "The Spaceley Sprocket migration tool returned HTTP 500 in the EMEA sandbox (George Jetson / Rocket Pack Express).",
      cause:
        "Sandbox vs production certificate SAN mismatch. Similar DEMO tickets AJ18268 and AJ18600. The generic HTTP 500 runbook was discarded.",
      fix: "Reissue the sandbox certificate with the matching SAN, then re-run the migration. Do not patch the wizard for a generic 500.",
    },
    "CONNECTOR-LAG": {
      title: "Signal connector is not running",
      observation: "1 of 5 GaussIQ 1.0 demo services is not ready: signal-connector (5 restarts).",
      cause: "Ticketing signals are not landing, so Case Intelligence similar-case evidence goes stale.",
      fix: "Restore signal-connector before trusting empty case plans. Empty evidence is not a missing KB article.",
    },
    "SKILL-GAP-TLS": {
      title: "No one on this shift has recent cert troubleshooting",
      observation: "TLS / certificate troubleshooting demand=High coverage=0 recency_days=240.",
      cause: "AJ18991 needs a cert SAN check. Nobody on this EMEA shift has closed a cert case in 240 days.",
      fix: "Pair AJ18991 with someone who has closed a cert case, or treat this as a training gap. Do not auto-assign from a model.",
    },
    "AUTH-OPEN": {
      title: "Case Intelligence API is reachable without signing in",
      observation: "Mocked case-intel-api GraphQL answered without a session cookie.",
      cause: "Auth is not required on this demo endpoint. This is a fixture finding, not a live exploit.",
      fix: "Require a session on case-intel-api before serving case plans. A 200 from /health is not proof that auth is on.",
    },
    "SECRET-IN-LOG": {
      title: "Token-like value in a service log (redacted)",
      observation: "A token-like value appeared in rec-engine logs. Shown redacted: giq_lab_****redacted****.",
      cause: "The recommendation engine echoed an Authorization header. The raw value is never shown here.",
      fix: "Stop logging Authorization headers. Rotate the lab token.",
    },
  };

  const RULED_OUT = {
    "APP-CODE-500":
      "Checked — not the cause. The 500 is the TLS SAN mismatch on AJ18991, not a defect in the SFM wizard code.",
    "CPU-HOT": "Checked — not the cause. No sampled GaussIQ 1.0 service is at ≥80% of its CPU limit.",
    "INSIGHTS-DOWN":
      "Checked — not the cause. Management Insights API is Running. Stale case plans come from the connector, not Insights being down.",
    "TLS-MISSING":
      "Checked — not the cause. case-intel-api already has TLS. Open GraphQL is an auth gap, not a missing certificate on GaussIQ itself.",
    "LIVE-SCAN": "Checked — not the cause. This lab never scans the internet. Findings come only from the security fixture.",
  };

  function redactSecrets(text) {
    return String(text || "").replace(
      /(Bearer\s+)(?!giq_lab_\*+redacted)\S+/gi,
      "$1giq_lab_****redacted****"
    );
  }

  function rcaCard(f) {
    const sev = String(f.severity || "high").toLowerCase();
    const plain = (f.id && PLAIN_CAUSE[f.id]) || {};
    const observation = redactSecrets(plain.observation || f.observation || f.symptom || "");
    const cause = redactSecrets(plain.cause || f.likely_cause || f.cause || "");
    const fix = redactSecrets(plain.fix || f.suggested || f.recommendation || f.fix || "");
    const title = plain.title || f.title || f.name || "Finding";
    const id = f.id ? f.id + " · " : "";
    return `<article class="finding ${sev}">
      <strong>${id}${title}</strong>
      <dl>
        <dt>Symptom</dt><dd>${observation}</dd>
        <dt>Cause</dt><dd>${cause}</dd>
        <dt>Fix</dt><dd><em>${fix}</em></dd>
      </dl>
    </article>`;
  }

  function renderRca(extra, engine) {
    const report = engine || (state.data && state.data.rca_report);
    const parts = [];
    parts.push(
      '<p class="hint">HTTP 500 is a symptom. This snapshot is a certificate SAN mismatch on AJ18991 plus a crash-looping signal connector.</p>'
    );
    const seen = {};
    const cards = [];
    function addCard(f) {
      const id = f && f.id;
      if (id && seen[id]) return;
      if (id) seen[id] = true;
      cards.push(rcaCard(f));
    }
    (extra || []).forEach((r) =>
      addCard({
        severity: "high",
        id: r.id,
        title: r.name,
        observation: r.symptom,
        cause: r.cause,
        recommendation: r.fix,
      })
    );
    (report && report.fired ? report.fired : []).forEach(addCard);
    parts.push(cards.join(""));
    const skipped = (report && report.skipped) || [];
    if (skipped.length) {
      parts.push('<h2 class="skipped-h">Checked — not the cause</h2>');
      parts.push(
        skipped
          .map((row) => {
            const body = RULED_OUT[row.id] || row.why || "";
            return `<article class="finding skipped"><strong>${row.id}</strong><p>${body}</p></article>`;
          })
          .join("")
      );
    }
    const html = parts.join("");
    ["rca-list", "health-rca-list"].forEach((id) => {
      const el = $(id);
      if (el) el.innerHTML = html;
    });
  }

  function renderSecurity(report) {
    const engine = report || (state.data && state.data.security_report) || { fired: [], skipped: [] };
    const findings = $("sec-findings");
    const rcaList = $("sec-rca-list");
    if (!findings || !rcaList) return;
    const fired = engine.fired || [];
    findings.innerHTML =
      '<h2 class="skipped-h">Current findings</h2>' +
      fired
        .map((f) => {
          const plain = (f.id && PLAIN_CAUSE[f.id]) || {};
          return (
            '<article class="finding ' +
            String(f.severity || "high").toLowerCase() +
            '"><strong>' +
            escapeHtml((f.id ? f.id + " · " : "") + (plain.title || f.title || "Finding")) +
            "</strong><p>" +
            escapeHtml(redactSecrets(plain.observation || f.observation || "")) +
            "</p></article>"
          );
        })
        .join("");
    const rcaParts = fired.map(rcaCard);
    const skipped = engine.skipped || [];
    if (skipped.length) {
      rcaParts.push('<h2 class="skipped-h">Checked — not the cause</h2>');
      skipped.forEach((row) => {
        const body = RULED_OUT[row.id] || redactSecrets(row.why || "");
        rcaParts.push(
          '<article class="finding skipped"><strong>' +
            escapeHtml(row.id) +
            "</strong><p>" +
            escapeHtml(body) +
            "</p></article>"
        );
      });
    }
    rcaList.innerHTML = rcaParts.join("");
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function renderServices() {
    const rows = state.data.fixtures.services.services;
    $("svc-body").innerHTML = rows
      .map((s) => {
        const statusClass =
          s.status === "CrashLoopBackOff" ? "status-bad" : s.restarts ? "status-warn" : "status-ok";
        return `<tr>
          <td>${s.id}</td>
          <td>${s.product}</td>
          <td class="${statusClass}">${s.status}</td>
          <td>${s.restarts}</td>
          <td>${s.cpu_pct}%</td>
          <td>${s.memory_mib} / ${s.memory_limit_mib} MiB</td>
        </tr>`;
      })
      .join("");
  }

  function renderCases() {
    const items = state.data.fixtures.cases.items;
    const rows = items
      .map(
        (c) => `<tr>
          <td>${c.id}</td>
          <td>${c.customer}</td>
          <td>${c.org}</td>
          <td>${c.severity}</td>
          <td>${c.symptom}</td>
          <td>${c.likely_cause}</td>
        </tr>`
      )
      .join("");
    $("case-table").innerHTML =
      `<table><thead><tr><th>Id</th><th>Customer</th><th>Org</th><th>Severity</th><th>Symptom</th><th>Likely cause</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderSkills() {
    const items = state.data.fixtures.skills.items;
    const rows = items
      .map(
        (s) => `<tr>
          <td>${s.skill}</td>
          <td>${s.demand}</td>
          <td>${s.coverage}</td>
          <td>${s.recency_days}</td>
          <td>${s.why}</td>
        </tr>`
      )
      .join("");
    $("skill-table").innerHTML =
      `<table><thead><tr><th>Skill</th><th>Demand</th><th>Coverage</th><th>Recency (days)</th><th>Why</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function sizeCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    const dpr = window.devicePixelRatio || 1;
    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    return { ctx, width, height };
  }

  function drawBars(canvasId, rows) {
    const canvas = $(canvasId);
    if (!canvas) return;
    const { ctx, width, height } = sizeCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    if (!rows.length) return;
    const max = Math.max.apply(null, rows.map((r) => r.value)) || 1;
    const gap = 12;
    const barW = (width - gap * (rows.length + 1)) / rows.length;
    rows.forEach((row, i) => {
      const h = ((row.value / max) * (height - 28)) | 0;
      const x = gap + i * (barW + gap);
      const y = height - 18 - h;
      ctx.fillStyle = row.color;
      ctx.fillRect(x, y, barW, h);
      ctx.fillStyle = "#8aa297";
      ctx.font = "11px IBM Plex Sans, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(row.label, x + barW / 2, height - 6);
      ctx.fillStyle = "#eef4ef";
      ctx.fillText(String(row.value), x + barW / 2, y - 4);
    });
  }

  function renderPerformance() {
    const p = state.data.fixtures.performance;
    const b = p.baseline;
    $("perf-body").innerHTML = [
      ["Gross MTTR (h)", p.gross_mttr_hours, b.gross_mttr_hours],
      ["Net MTTR (h)", p.net_mttr_hours, b.net_mttr_hours],
      ["Eng assist (h)", p.eng_assist_hours, b.eng_assist_hours],
    ]
      .map((row) => `<tr><td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td></tr>`)
      .join("");
    drawBars("mttr-chart", [
      { label: "gross", value: p.gross_mttr_hours, color: "#7eb0e4" },
      { label: "net", value: p.net_mttr_hours, color: "#8fd6b8" },
      { label: "assist", value: p.eng_assist_hours, color: COLORS["rec-engine"] },
      { label: "gross base", value: b.gross_mttr_hours, color: "#5a6e66" },
    ]);
    drawBars("vol-chart", [
      { label: "open", value: p.open_cases, color: "#e05d4f" },
      { label: "resolved 7d", value: p.resolved_7d, color: "#3dba7a" },
    ]);
  }

  function renderSuitePanel(summary) {
    if (!summary) return;
    state.lastSuite = summary;
    const hint = $("suite-hint");
    hint.textContent =
      summary.suite +
      (summary.layer ? " / " + summary.layer : "") +
      " → " +
      summary.verdict +
      " · " +
      summary.passed +
      " passed · " +
      summary.failed +
      " failed · " +
      summary.duration_ms +
      " ms";
    $("suite-live").textContent = summary.suite + " " + summary.verdict;
    $("suite-live").parentElement.classList.toggle("degraded", summary.verdict === "FAIL");
    $("suite-live").parentElement.classList.toggle("ok", summary.verdict === "PASS");
    drawBars("suite-chart", [
      { label: "pass", value: summary.passed, color: "#3dba7a" },
      { label: "fail", value: summary.failed, color: "#e05d4f" },
    ]);
    const layers = {};
    (summary.cases || []).forEach((c) => {
      layers[c.layer] = layers[c.layer] || { n: 0 };
      layers[c.layer].n += 1;
    });
    drawBars(
      "layer-chart",
      Object.keys(layers).map((k, i) => ({
        label: k,
        value: layers[k].n,
        color: ["#7eb0e4", "#c4a35a", "#c792ea"][i % 3],
      }))
    );
    const rows = (summary.cases || [])
      .map(
        (c) => `<tr>
          <td class="badge ${c.status}">${c.status.toUpperCase()}</td>
          <td>${c.layer}</td>
          <td>${c.name}</td>
          <td>${c.duration_ms} ms</td>
        </tr>`
      )
      .join("");
    $("suite-table").innerHTML =
      `<table><thead><tr><th>Result</th><th>Layer</th><th>Case</th><th>Time</th></tr></thead><tbody>${rows}</tbody></table>`;
    if (summary.rcas && summary.rcas.length) renderRca(summary.rcas);
  }

  function renderQuestionBank() {
    const root = $("qbank");
    if (!root) return;
    const bank = (state.data && state.data.questions) || [];
    root.innerHTML = "";
    bank.forEach((cat) => {
      const section = document.createElement("section");
      const h = document.createElement("h3");
      h.textContent = cat.title;
      section.appendChild(h);
      (cat.questions || []).forEach((q) => {
        const row = document.createElement("div");
        row.className = "qbank-row";
        const code = document.createElement("code");
        code.textContent = q;
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Copy";
        btn.dataset.copy = q;
        btn.setAttribute("data-testid", "qbank-copy");
        btn.addEventListener("click", () => copyQuestion(btn, q));
        row.appendChild(code);
        row.appendChild(btn);
        section.appendChild(row);
      });
      root.appendChild(section);
    });
  }

  function copyQuestion(btn, text) {
    btn.textContent = "Copied";
    btn.classList.add("copied");
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).catch(function () {});
    }
    setTimeout(() => {
      btn.textContent = "Copy";
      btn.classList.remove("copied");
    }, 1600);
  }

  function toggleQuestionBank() {
    const panel = $("qbank");
    const btn = $("btn-qbank");
    if (!panel || !btn) return;
    const open = panel.classList.contains("hidden") || panel.hidden;
    panel.classList.toggle("hidden", !open);
    panel.hidden = !open;
    btn.setAttribute("aria-expanded", open ? "true" : "false");
    if (open) renderQuestionBank();
  }

  function paintAppHealth() {
    if (!state.data || !window.GiqLabRouter) return null;
    const snapshot = window.GiqLabRouter.computeAppHealth(state.data, {
      lastSmoke: state.lastSmoke,
      lastSanity: state.lastSanity,
    });
    const health = snapshot.health || "DEGRADED";
    const el = $("health-live");
    if (!el) return snapshot;
    el.textContent = health;
    const kpi = el.parentElement;
    if (kpi) {
      kpi.classList.toggle("ok", health === "HEALTHY");
      kpi.classList.toggle("degraded", health === "DEGRADED");
      kpi.classList.toggle("critical", health === "CRITICAL");
    }
    return snapshot;
  }

  function showTab(id) {
    document.querySelectorAll(".tab").forEach((t) => {
      const on = t.dataset.tab === id;
      t.classList.toggle("on", on);
      t.setAttribute("aria-selected", on ? "true" : "false");
    });
    document.querySelectorAll(".tab-panel").forEach((p) => {
      p.classList.toggle("on", p.id === "tab-" + id);
    });
  }

  function addStructured(el, result) {
    if (result.awaiting_regression) {
      const row = document.createElement("div");
      row.className = "confirm";
      row.innerHTML =
        '<button type="button" data-confirm="yes">Run regression</button>' +
        '<button type="button" data-confirm="no">Skip</button>';
      row.addEventListener("click", (e) => {
        const btn = e.target.closest("button");
        if (!btn) return;
        ask(btn.dataset.confirm === "yes" ? "yes" : "no");
      });
      el.appendChild(row);
    }
  }

  function addMsg(kind, text, result) {
    const el = document.createElement("div");
    el.className = "msg " + kind;
    const isSuite =
      result &&
      result.report &&
      (result.ui === "suite_report" || result.ui === "suite_explain" || result.route === "run_suite");
    if (kind === "bot" && isSuite && window.GiqLabRouter && window.GiqLabRouter.renderSuiteCard) {
      window.GiqLabRouter.renderSuiteCard(el, result);
    } else {
      const body = document.createElement("div");
      body.className = "body";
      body.textContent = text;
      el.appendChild(body);
    }
    if (result && !isSuite) {
      const chips = document.createElement("div");
      chips.className = "chips";
      const kindChip = document.createElement("span");
      const kindName = result.source_kind || "handler";
      kindChip.className = "chip kind-" + kindName;
      kindChip.dataset.testid = "source-kind";
      kindChip.textContent = result.source_label || kindName;
      chips.appendChild(kindChip);
      const source = document.createElement("span");
      source.className = "chip source";
      source.dataset.testid = "result-source";
      source.textContent = "source " + result.source;
      chips.appendChild(source);
      const route = document.createElement("span");
      route.className = "chip";
      route.textContent = "route " + result.route;
      chips.appendChild(route);
      if (result.metrics && result.metrics.verdict) {
        const v = document.createElement("span");
        v.className = "chip " + (result.metrics.verdict === "PASS" ? "ok" : "bad");
        v.textContent = result.metrics.verdict;
        chips.appendChild(v);
      }
      (result.tools || []).slice(0, 4).forEach((tool) => {
        const t = document.createElement("span");
        t.className = "chip";
        t.textContent = tool;
        chips.appendChild(t);
      });
      el.appendChild(chips);
    }
    if (result) addStructured(el, result);
    $("log").appendChild(el);
    $("log").scrollTop = $("log").scrollHeight;
  }

  function applySession(result) {
    if (result && result.session_update) {
      Object.assign(state.session, result.session_update);
    } else if (result && result.awaiting_regression) {
      state.session.awaiting_regression = true;
    }
  }

  function ask(question) {
    const q = String(question || "").trim();
    if (!q) return null;
    $("q").value = "";
    $("q").focus();
    addMsg("user", q);
    const result = window.GiqLabRouter.route(state.data, q, state.session);
    applySession(result);
    addMsg("bot", result.answer, result);
    if (result.ui === "suite_report") {
      showTab("suites");
      renderSuitePanel(result.report);
      if (result.report && result.report.suite === "smoke") state.lastSmoke = result.report;
      if (result.report && result.report.suite === "sanity") state.lastSanity = result.report;
      paintAppHealth();
    }
    if (result.ui === "verdict") {
      if (result.health && result.health.smoke_report) state.lastSmoke = result.health.smoke_report;
      if (result.health && result.health.sanity_report) {
        state.lastSanity = result.health.sanity_report;
        renderSuitePanel(result.health.sanity_report);
      }
      paintAppHealth();
      renderRca();
    }
    if (result.ui === "rca") {
      renderRca(null, result.rca);
    }
    if (result.ui === "security") {
      renderSecurity(result.security);
    }
    if (result.ui === "skills") showTab("skills");
    if (result.ui === "health") {
      renderRca(null, result.rca);
    }
    return result;
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function connectValues() {
    return {
      tenant: $("c-tenant").value.trim(),
      queue: $("c-queue").value.trim(),
      region: $("c-region").value.trim(),
      pack: $("c-pack").value.trim(),
      token: $("c-token").value.trim(),
      user: $("c-user").value.trim(),
    };
  }

  function appendConnectStep(text, cls) {
    const log = $("connect-log");
    log.hidden = false;
    const li = document.createElement("li");
    li.textContent = text;
    if (cls) li.className = cls;
    log.appendChild(li);
  }

  async function runConnect() {
    const btn = $("btn-connect");
    if (btn.disabled) return;
    const vals = connectValues();
    const missing = ["tenant", "queue", "region", "pack", "token", "user"].filter((k) => !vals[k]);
    $("connect-log").innerHTML = "";
    $("connect-log").hidden = false;
    if (missing.length) {
      appendConnectStep("Validate failed — fill: " + missing.join(", ") + ". Dummy values are enough; nothing is sent.", "run");
      return;
    }
    btn.disabled = true;
    const steps = [
      "Validate tenant `" + vals.tenant + "` queue `" + vals.queue + "` region `" + vals.region + "`",
      "Attach mock signal pack `" + vals.pack + "` (simulated — no live ticketing call)",
      "Write in-memory lab session for `" + vals.user + "` (not stored, gone on refresh)",
      "Read GaussIQ 1.0 demo service fixture (case / skills / insights / connector / rec-engine)",
      "Start 24x7 health + hybrid QA agent chatbot",
    ];
    for (const line of steps) {
      appendConnectStep(line, "run");
      await sleep(280);
    }
    appendConnectStep("Connected. Monitoring is on for this page session only.", "ok");
    startMonitoring(vals);
    btn.disabled = false;
  }

  function startMonitoring(vals) {
    state.connected = true;
    state.session.tenant = vals.tenant;
    state.session.queue = vals.queue;
    const hero = document.querySelector(".page-hero");
    if (hero) hero.classList.add("hidden");
    $("connect-gate").classList.add("hidden");
    $("monitor").classList.remove("hidden");
    renderServices();
    renderCases();
    renderSkills();
    renderPerformance();
    renderRca();
    renderSecurity();
    renderQuestionBank();
    const perf = state.data.fixtures.performance;
    $("cases-live").textContent = String(perf.open_cases);
    $("mttr-live").textContent = String(perf.gross_mttr_hours) + " h";
    $("assist-live").textContent = String(perf.eng_assist_hours) + " h";
    state.lastSmoke = window.GiqLabRouter.runSuite(state.data, "smoke", null);
    state.lastSanity = window.GiqLabRouter.runSuite(state.data, "sanity", null);
    const snapshot = paintAppHealth();
    renderSuitePanel(state.lastSanity);
    const canned = $("canned");
    canned.innerHTML = "";
    state.data.canned.forEach((q) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.q = q;
      btn.textContent = q;
      canned.appendChild(btn);
    });
    addMsg(
      "bot",
      "Connected to tenant `" +
        vals.tenant +
        "` queue `" +
        vals.queue +
        "` (simulated, not live production). Quality of GaussIQ 1.0 is " +
        ((snapshot && snapshot.health) || "DEGRADED") +
        " from the fixture (signal-connector CrashLoopBackOff, CERT-MISMATCH on AJ18991, AUTH-OPEN on case-intel-api). The dashboard above is the quality view — service health, MTTR vs baseline, security, RCA fire/skip. Try: current quality of 1.0, any security issues, why MTTR is high, run API smoke on case-plan APIs.",
      { source: "fallback:deterministic", route: "hello", tools: [] }
    );
  }

  function bind() {
    $("ask").addEventListener("click", () => {
      const q = $("q").value.trim();
      if (q) ask(q);
    });
    $("q").addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const q = $("q").value.trim();
        if (q) ask(q);
      }
    });
    $("canned").addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (btn) ask(btn.dataset.q);
    });
    $("btn-qbank").addEventListener("click", toggleQuestionBank);
    document.querySelector(".tabs").addEventListener("click", (e) => {
      const tab = e.target.closest(".tab");
      if (tab) showTab(tab.dataset.tab);
    });
    $("btn-connect").addEventListener("click", () => {
      runConnect();
    });
  }

  async function main() {
    const res = await fetch("js/gaussiq-data.json");
    state.data = await res.json();
    bind();
  }

  window.GiqLab = { ask, state, runConnect };
  main();
})();
