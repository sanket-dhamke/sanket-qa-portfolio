(function () {
  const COLORS = {
    "datahub-gms": "#7eb0e4",
    "datahub-frontend": "#8fd6b8",
    "datahub-mae-consumer": "#e05d4f",
    "datahub-mce-consumer": "#c4a35a",
    "datahub-actions": "#c792ea",
  };
  const MAX_POINTS = 40;
  const state = {
    data: null,
    series: {},
    tick: 0,
    ingestBoost: 0,
    highlighted: null,
    extraAssets: 0,
    running: null,
    session: { awaiting_regression: false },
    lastSuite: null,
    connected: false,
    email: {
      signatures: [],
      log: [],
      lastSent: null,
      nextAt: null,
    },
  };

  const $ = (id) => document.getElementById(id);

  function clamp(n, lo, hi) {
    return Math.max(lo, Math.min(hi, n));
  }

  function seedSeries(workers) {
    workers.forEach((w) => {
      state.series[w.component] = {
        cpu: Array.from({ length: MAX_POINTS }, () => w.cpu_pct),
        mem: Array.from({ length: MAX_POINTS }, () => w.memory_mib),
        limit: w.memory_limit_mib,
        baseCpu: w.cpu_pct,
        baseMem: w.memory_mib,
        pod: w.pod,
      };
    });
  }

  function current(component) {
    const s = state.series[component];
    return { cpu: s.cpu[s.cpu.length - 1], mem: s.mem[s.mem.length - 1], limit: s.limit, pod: s.pod };
  }

  function stepMetrics() {
    state.tick += 1;
    const t = state.tick;
    Object.keys(state.series).forEach((name, i) => {
      const s = state.series[name];
      const noise = Math.sin((t + i * 7) / 6) * 3.2 + (Math.random() * 2.4 - 1.2);
      let cpu = s.baseCpu + noise;
      let mem = s.baseMem + Math.sin((t + i * 5) / 8) * 18 + (Math.random() * 10 - 5);
      if (name === "datahub-mae-consumer") {
        cpu = clamp(s.baseCpu + Math.abs(noise) + 4, 70, 99);
        mem = s.limit;
      }
      if (state.ingestBoost > 0) {
        if (name === "datahub-actions") {
          cpu += 48 * state.ingestBoost;
          mem += 180 * state.ingestBoost;
        }
        if (name === "datahub-gms") {
          cpu += 16 * state.ingestBoost;
          mem += 90 * state.ingestBoost;
        }
      }
      s.cpu.push(clamp(cpu, 1, 99.5));
      s.mem.push(clamp(mem, 80, s.limit));
      if (s.cpu.length > MAX_POINTS) s.cpu.shift();
      if (s.mem.length > MAX_POINTS) s.mem.shift();
    });
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

  function drawChart(canvasId, key, maxFn) {
    const canvas = $(canvasId);
    if (!canvas) return;
    const { ctx, width, height } = sizeCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    ctx.strokeStyle = "#24344c";
    ctx.lineWidth = 1;
    for (let g = 1; g < 4; g++) {
      const y = (height / 4) * g;
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }
    Object.keys(state.series).forEach((name) => {
      const values = state.series[name][key];
      const max = maxFn(name);
      ctx.beginPath();
      ctx.strokeStyle = COLORS[name];
      ctx.lineWidth = state.highlighted === name ? 2.4 : 1.4;
      ctx.globalAlpha = !state.highlighted || state.highlighted === name ? 1 : 0.25;
      values.forEach((v, i) => {
        const x = (i / (MAX_POINTS - 1)) * width;
        const y = height - (v / max) * (height - 8) - 4;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      });
      ctx.stroke();
      ctx.globalAlpha = 1;
    });
  }

  function drawBars(canvasId, rows, opts) {
    const canvas = $(canvasId);
    if (!canvas) return;
    const { ctx, width, height } = sizeCanvas(canvas);
    ctx.clearRect(0, 0, width, height);
    if (!rows.length) return;
    const scale = (v) => (opts && opts.log ? Math.log10(Math.max(v, 1)) : v);
    const max = Math.max.apply(null, rows.map((r) => scale(r.value))) || 1;
    const gap = 12;
    const barW = (width - gap * (rows.length + 1)) / rows.length;
    rows.forEach((row, i) => {
      const h = ((scale(row.value) / max) * (height - 28)) | 0;
      const x = gap + i * (barW + gap);
      const y = height - 18 - h;
      ctx.fillStyle = row.color;
      ctx.fillRect(x, y, barW, h);
      ctx.fillStyle = "#8b9cb3";
      ctx.font = "11px IBM Plex Sans, sans-serif";
      ctx.textAlign = "center";
      ctx.fillText(row.label, x + barW / 2, height - 6);
      ctx.fillStyle = "#e8eef8";
      ctx.fillText(String(row.value), x + barW / 2, y - 4);
    });
  }

  function renderPods() {
    const cluster = state.data.fixtures.cluster;
    const body = cluster.pods
      .map((pod) => {
        const live = current(pod.component);
        const statusClass =
          pod.status === "CrashLoopBackOff" ? "status-bad" : pod.restarts ? "status-warn" : "status-ok";
        return `<tr>
          <td>${pod.component}</td>
          <td class="${statusClass}">${pod.status}</td>
          <td>${pod.restarts}</td>
          <td>${pod.last_reason || "—"}</td>
          <td>${live.cpu.toFixed(1)}%</td>
          <td>${Math.round(live.mem)} / ${pod.memory_limit_mib} MiB</td>
        </tr>`;
      })
      .join("");
    $("pod-body").innerHTML = body;
    $("error-log").textContent = cluster.pods
      .filter((p) => p.status !== "Running" || p.last_reason)
      .map((p) => `${p.component}  restarts=${p.restarts}  ${p.last_reason || p.status}  ${p.probe || ""}`)
      .join("\n");
  }

  function rcaCard(f) {
    const sev = String(f.severity || "high").toLowerCase();
    const observation = f.observation || f.evidence || f.symptom || "";
    const cause = f.likely_cause || f.cause || "";
    const fix = f.suggested || f.recommendation || f.fix || "";
    const id = f.id ? f.id + " · " : "";
    return `<article class="finding ${sev}">
      <strong>${id}${f.component ? f.component + " · " : ""}${f.title || f.name || "Finding"}</strong>
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
    if (report && report.principle) {
      parts.push(`<p class="hint">${report.principle}</p>`);
    }
    const fired = report && report.fired && report.fired.length
      ? report.fired.map(rcaCard)
      : (state.data.fixtures.rca.findings || []).map(rcaCard);
    parts.push(fired.join(""));
    const more = (extra || []).map((r) =>
      rcaCard({
        severity: "high",
        id: r.id,
        component: r.component,
        title: r.name,
        evidence: r.symptom,
        likely_cause: r.cause,
        suggested: r.fix,
      })
    );
    if (more.length) parts.unshift(more.join(""));
    if (report && report.skipped && report.skipped.length) {
      parts.push('<h2 class="skipped-h">Evaluated, not fired</h2>');
      parts.push(
        '<p class="hint">A skipped rule is still a diagnosis: OOM vs probe, heap already set, no idle sizing all-clear.</p>'
      );
      parts.push(
        report.skipped
          .map(
            (row) =>
              `<article class="finding skipped"><strong>${row.id} not fired</strong><p>${row.why}</p></article>`
          )
          .join("")
      );
    }
    $("rca-list").innerHTML = parts.join("");
  }

  function renderLegend() {
    $("legend").innerHTML = Object.keys(COLORS)
      .map((name) => `<span><i style="background:${COLORS[name]}"></i>${name}</span>`)
      .join("");
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
      layers[c.layer] = layers[c.layer] || { pass: 0, fail: 0 };
      if (c.status === "pass") layers[c.layer].pass += 1;
      else layers[c.layer].fail += 1;
    });
    drawBars(
      "layer-chart",
      Object.keys(layers).map((k, i) => ({
        label: k,
        value: layers[k].pass + layers[k].fail,
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

  function renderTools() {
    const bundle = ((state.data.fixtures || {}).tools) || {};
    const tools = bundle.tools || [];
    const hint = $("tool-hint");
    if (hint) {
      hint.textContent =
        (bundle.note || "Lab tool catalog.") +
        " The keyword table chooses which tool runs. A model never does. " +
        "CPU/memory percentages are of each pod's own limit, not node capacity.";
    }
    const rows = tools
      .map((t) => {
        const kind = t.gms ? "GMS GraphQL" : "cluster fixture";
        const cls = t.gms ? "gms" : "cluster";
        return `<tr>
          <td><code>${t.id}</code></td>
          <td class="badge ${cls}">${kind}</td>
          <td>${t.needs}</td>
          <td>${t.returns}</td>
        </tr>`;
      })
      .join("");
    $("tool-table").innerHTML =
      `<table><thead><tr><th>Tool</th><th>Kind</th><th>Reads</th><th>Returns</th></tr></thead><tbody>${rows}</tbody></table>`;
  }

  function renderCapacity(plan) {
    if (!plan) return;
    const current = plan.current_assets || 140;
    drawBars(
      "cap-chart",
      [
        { label: "now", value: current, color: "#7eb0e4" },
        { label: "1M", value: 1000000, color: "#c4a35a" },
        { label: "10M", value: 10000000, color: "#e05d4f" },
      ],
      { log: true }
    );
    const blocks = plan.plans || [];
    $("cap-table").innerHTML = blocks
      .map((block) => {
        const rows = (block.changes || [])
          .map(
            (c) =>
              `<tr><td>${c.component}</td><td>${c.from}</td><td>${c.to}</td></tr>`
          )
          .join("");
        return `<h2 style="border:0">${block.label}</h2>
          <table><thead><tr><th>Component</th><th>Now</th><th>Upgrade</th></tr></thead><tbody>${rows}</tbody></table>`;
      })
      .join("");
  }

  function addStructured(el, result) {
    if (result.ui === "suite_report" && result.report) {
      const wrap = document.createElement("div");
      wrap.className = "result-table";
      wrap.innerHTML = `<table>${(result.report.cases || [])
        .map(
          (c) =>
            `<tr><td class="badge ${c.status}">${c.status.toUpperCase()}</td><td>${c.layer}</td><td>${c.name}</td></tr>`
        )
        .join("")}</table>`;
      el.appendChild(wrap);
    }
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
    const body = document.createElement("div");
    body.className = "body";
    body.textContent = text;
    el.appendChild(body);
    if (result) {
      const chips = document.createElement("div");
      chips.className = "chips";
      const kind = document.createElement("span");
      const kindName = result.source_kind || "handler";
      kind.className = "chip kind-" + kindName;
      kind.dataset.testid = "source-kind";
      kind.textContent = result.source_label || kindName;
      chips.appendChild(kind);
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
      addStructured(el, result);
    }
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
    const result = window.LabRouter.route(state.data, q, state.session);
    applySession(result);
    addMsg("bot", result.answer, result);
    if (result.metrics && result.metrics.filter) state.highlighted = result.metrics.filter;
    else if (result.route === "pod_status") state.highlighted = "datahub-mae-consumer";
    else state.highlighted = null;
    if (result.ui === "recipe_editor") openRecipe(result.recipe);
    if (result.ui === "suite_report") {
      showTab("suites");
      renderSuitePanel(result.report);
      if (result.report && result.report.rcas && result.report.rcas.length) showTab("suites");
    }
    if (result.ui === "verdict") {
      showTab("rca");
      const health = result.metrics && result.metrics.health;
      $("health-live").textContent = health || "—";
      $("health-live").parentElement.classList.toggle("degraded", health === "DEGRADED");
      $("health-live").parentElement.classList.toggle("ok", health === "HEALTHY");
      if (result.health && result.health.sanity_report) renderSuitePanel(result.health.sanity_report);
    }
    if (result.ui === "rca") {
      showTab("rca");
      renderRca(null, result.rca);
    }
    if (result.ui === "capacity") {
      showTab("capacity");
      renderCapacity(result.capacity);
    }
    if (result.ui === "tools") {
      showTab("tools");
      renderTools();
    }
    if (result.metrics && result.metrics.open != null) {
      $("alert-live").textContent = String(result.metrics.open);
    }
    return result;
  }

  function field(yaml, key) {
    const match = yaml.match(new RegExp("^\\s*" + key + ":\\s*['\"]?([^\\n#'\"]+)", "m"));
    return match ? match[1].trim() : "";
  }

  function syncYamlFromForm() {
    const pipeline = $("f-pipeline").value.trim() || "postgres-lab-demo";
    const host = $("f-host").value.trim();
    const user = $("f-user").value.trim();
    const database = $("f-db").value.trim();
    const schemas = $("f-schema").value.split(",").map((s) => s.trim()).filter(Boolean);
    const tables = $("f-table").value.split(",").map((s) => s.trim()).filter(Boolean);
    const schemaYaml = schemas.map((s) => `        - ${s}`).join("\n") || "        - public";
    const tableYaml = tables.map((s) => `        - ${s}`).join("\n") || "        - public.orders";
    $("recipe-yaml").value = `pipeline_name: ${pipeline}
source:
  type: postgres
  config:
    host_port: ${host}
    database: ${database}
    username: ${user}
    password: \${POSTGRES_PASSWORD}
    include_tables: true
    include_views: true
    schema_pattern:
      allow:
${schemaYaml}
    table_pattern:
      allow:
${tableYaml}
sink:
  type: datahub-rest
  config:
    server: http://datahub-gms:8080
`;
  }

  function allowList(yaml, section) {
    const match = yaml.match(new RegExp(section + ":[\\s\\S]*?allow:\\s*((?:\\n\\s*-\\s+.+)*)"));
    if (!match) return "";
    return Array.from(match[1].matchAll(/-\s+(\S+)/g))
      .map((x) => x[1].trim())
      .join(", ");
  }

  function fillFormFromYaml(yaml) {
    const text = String(yaml || "").trim();
    $("f-pipeline").value = field(text, "pipeline_name");
    $("f-host").value = field(text, "host_port");
    $("f-user").value = field(text, "username");
    $("f-db").value = field(text, "database");
    $("f-schema").value = allowList(text, "schema_pattern") || "public, reporting";
    $("f-table").value = allowList(text, "table_pattern") || "public.orders, public.customers";
    $("recipe-yaml").value = text + "\n";
  }

  function openRecipe(recipe) {
    $("ingest-panel").classList.remove("hidden");
    fillFormFromYaml(recipe || state.data.recipes.postgres);
    $("ingest-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function validateRecipe(yaml) {
    const missing = [];
    if (!/type:\s*postgres/.test(yaml)) missing.push("source.type: postgres");
    ["host_port", "username", "database"].forEach((key) => {
      if (!field(yaml, key)) missing.push(key);
    });
    if (!/schema_pattern:/.test(yaml)) missing.push("schema_pattern.allow");
    return missing;
  }

  function appendLog(line) {
    const box = $("run-log");
    box.textContent += line + "\n";
    box.scrollTop = box.scrollHeight;
  }

  function setProgress(pct) {
    $("bar").style.width = pct + "%";
    $("progress-label").textContent = pct + "%";
  }

  function submitRecipe() {
    const yaml = $("recipe-yaml").value;
    const missing = validateRecipe(yaml);
    if (missing.length) {
      addMsg(
        "bot",
        "Recipe is incomplete. This lab will not invent coordinates. Missing: " + missing.join(", ") + ".",
        { source: "handler:ingest_recipe", route: "ingest_recipe", tools: ["validate_recipe"] }
      );
      return;
    }
    const pipeline = field(yaml, "pipeline_name") || "postgres-lab-demo";
    const host = field(yaml, "host_port");
    const database = field(yaml, "database");
    const user = field(yaml, "username");
    const sourceUrn = "urn:li:dataHubIngestionSource:" + pipeline;
    const runId = "urn:li:dataHubExecutionRequest:exec-" + Date.now().toString(36);
    const recipeJson = JSON.stringify({
      pipeline_name: pipeline,
      source: { type: "postgres", config: { host_port: host, database: database, username: user } },
      sink: { type: "datahub-rest", config: { server: "http://datahub-gms:8080" } },
    });
    $("gql-create").textContent = `mutation {
  createIngestionSource(input: {
    name: "${pipeline}"
    type: "postgres"
    config: {
      executorId: "default"
      version: "0.14.1"
      recipe: ${JSON.stringify(recipeJson)}
    }
  })
}
# mock GMS → ${sourceUrn}`;
    $("gql-run").textContent = `mutation {
  createIngestionExecutionRequest(input: {
    ingestionSourceUrn: "${sourceUrn}"
  })
}
# mock GMS → ${runId}`;
    $("run-meta").innerHTML = `run id <code id="run-id">${runId}</code> · source <code>${sourceUrn}</code> · executor datahub-actions`;
    $("run-log").textContent = "";
    setProgress(0);
    addMsg(
      "bot",
      `Simulated GraphQL createIngestionSource → ${sourceUrn}\nthen createIngestionExecutionRequest → ${runId}\nExecutor: datahub-actions. Watch CPU/memory on this screen while the fake run streams.`,
      {
        source: "handler:ingest_recipe",
        route: "ingest_execute",
        tools: ["graphql:createIngestionSource", "graphql:createIngestionExecutionRequest"],
      }
    );
    startRun({ pipeline, host, database, user, runId });
  }

  function startRun(ctx) {
    if (state.running) clearInterval(state.running.timer);
    const steps = [
      [8, `[datahub-actions] executor accepted ${ctx.runId}`],
      [16, `[datahub-actions] pipeline=${ctx.pipeline} cli=0.14.1`],
      [24, `[postgres] connecting host_port=${ctx.host} database=${ctx.database} username=${ctx.user}`],
      [32, `[postgres] schema_pattern.allow applied; include_tables=true include_views=true`],
      [40, `[postgres] container DATABASE analytics → urn:li:container:analytics`],
      [48, `[postgres] container SCHEMA public`],
      [56, `[postgres] dataset urn:li:dataset:(urn:li:dataPlatform:postgres,analytics.public.orders,PROD) aspects=datasetProperties,schemaMetadata,container`],
      [64, `[postgres] dataset ...analytics.public.customers,PROD`],
      [70, `[datahub-gms] ingestProposal schemaMetadata ok`],
      [76, `[datahub-mae-consumer] WARN CrashLoopBackOff — MetadataAuditEvent_v4 lag, last_reason=OOMKilled`],
      [84, `[datahub-actions] memory high vs 2048Mi limit while emitting MCPs`],
      [92, `[datahub-mce-consumer] applied 14 MCEs`],
      [100, `[datahub-actions] SUCCESS datasets=14 containers=2 durationMs=18420`],
    ];
    let i = 0;
    state.ingestBoost = 0.35;
    state.highlighted = "datahub-actions";
    state.running = { timer: null };
    state.running.timer = setInterval(() => {
      if (i >= steps.length) {
        clearInterval(state.running.timer);
        state.ingestBoost = 0;
        return;
      }
      const [pct, line] = steps[i];
      state.ingestBoost = 0.35 + (i / steps.length) * 0.65;
      setProgress(pct);
      appendLog(line);
      if (pct === 100) {
        state.ingestBoost = 0;
        state.extraAssets += 14;
        $("asset-live").textContent = String(state.data.fixtures.ingestion.totals.assets + state.extraAssets);
      }
      i += 1;
    }, 700);
  }

  function tick() {
    if (!state.data || !state.connected) return;
    stepMetrics();
    drawChart("cpu-chart", "cpu", () => 100);
    drawChart("mem-chart", "mem", (name) => state.series[name].limit);
    renderPods();
  }

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function connectValues() {
    return {
      cluster: $("c-cluster").value.trim(),
      namespace: $("c-namespace").value.trim(),
      access: $("c-access").value.trim(),
      secret: $("c-secret").value.trim(),
      token: $("c-token").value.trim(),
      region: $("c-region").value.trim(),
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
    const missing = ["cluster", "namespace", "access", "secret", "region"].filter((k) => !vals[k]);
    $("connect-log").innerHTML = "";
    $("connect-log").hidden = false;
    if (missing.length) {
      appendConnectStep("Validate failed — fill: " + missing.join(", ") + ". Dummy values are enough; nothing is sent.", "run");
      return;
    }
    btn.disabled = true;
    const steps = [
      "Validate cluster `" + vals.cluster + "` ns `" + vals.namespace + "` region `" + vals.region + "`",
      "Assume identity for dummy key " + vals.access.slice(0, 8) + "… (simulated — no AWS call)",
      "Write in-memory kubeconfig for the DataHub lab context (not stored, gone on refresh)",
      "Pod read check against the fixture (datahub-gms, frontend, mae-consumer, mce-consumer, actions)",
      "Start performance monitoring + Hybrid AI Agent chatbot",
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
    state.session.cluster = vals.cluster;
    state.session.namespace = vals.namespace;
    $("connect-gate").classList.add("hidden");
    $("monitor").classList.remove("hidden");
    seedSeries(state.data.fixtures.metrics.workers);
    renderLegend();
    renderRca();
    renderTools();
    $("asset-live").textContent = String(state.data.fixtures.ingestion.totals.assets);
    $("source-live").textContent = String(state.data.fixtures.ingestion.sources.length);
    $("alert-live").textContent = String(state.data.fixtures.alerts.open);
    $("health-live").textContent = "unknown";
    const canned = $("canned");
    canned.innerHTML = "";
    state.data.canned.forEach((q) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.dataset.q = q;
      btn.textContent = q;
      canned.appendChild(btn);
    });
    tick();
    if (!state.tickTimer) state.tickTimer = setInterval(tick, 1000);
    renderCapacity({
      current_assets: state.data.fixtures.app_config.current_assets,
      plans: [],
    });
    addMsg(
      "bot",
      "Connected to `" +
        vals.cluster +
        "` ns `" +
        vals.namespace +
        "` (simulated). Hybrid AI Agent for performance testing. Keyword/hybrid router + suite catalog, not an LLM inventing metrics. CPU is % of pod limit. Ask to log in as emuser/empass, list the lab tools, run API or UI sanity, check alerts, size for 1M assets, or ask the current application state.",
      { source: "fallback:deterministic", route: "hello", tools: [] }
    );
  }

  function scheduleHours() {
    const picked = document.querySelector('input[name="email-every"]:checked');
    return Number((picked && picked.value) || "1");
  }

  function issueSignature(suites) {
    const fired = (((state.data.rca_report || {}).fired) || []).map((f) => f.id || f.title).join(",");
    const fails = suites
      .flatMap((s) => s.cases || [])
      .filter((c) => c.status === "fail")
      .map((c) => c.id)
      .join(",");
    const pods = (state.data.fixtures.cluster.pods || [])
      .filter((p) => p.status !== "Running" || p.last_reason)
      .map((p) => p.component + ":" + (p.last_reason || p.status))
      .join(",");
    return fired + "|" + fails + "|" + pods || "none";
  }

  function suiteOrder() {
    const extra = [];
    if ($("email-sanity").checked) extra.push("sanity");
    if ($("email-regression").checked) extra.push("regression");
    extra.push("smoke");
    return extra;
  }

  function runEmailSuites() {
    return suiteOrder().map((name) => window.LabRouter.runSuite(state.data, name, null));
  }

  function podLogLines() {
    return (state.data.fixtures.cluster.pods || [])
      .filter((p) => p.status !== "Running" || p.last_reason)
      .map((p) => {
        const bits = [
          "[" + p.component + "]",
          p.status,
          p.last_reason ? "last_reason=" + p.last_reason : "",
          p.last_exit_code != null ? "exit=" + p.last_exit_code : "",
          p.probe || "",
        ].filter(Boolean);
        return bits.join(" ");
      });
  }

  function suiteBlockHtml(summary) {
    const rows = (summary.cases || [])
      .map(
        (c) =>
          "<tr><td class='" +
          (c.status === "pass" ? "pass" : "fail") +
          "'>" +
          c.status.toUpperCase() +
          "</td><td>" +
          c.layer +
          "</td><td>" +
          c.name +
          "</td><td>" +
          (c.status === "fail" ? escapeHtml((c.actual || "") + " — expected " + (c.expected || "")) : c.duration_ms + " ms") +
          "</td></tr>"
      )
      .join("");
    const rcas = (summary.rcas || [])
      .map(
        (r) =>
          "<p><strong>Failure RCA — " +
          escapeHtml(r.name || r.id || "") +
          "</strong><br>Symptom: " +
          escapeHtml(r.symptom || "") +
          "<br>Cause: " +
          escapeHtml(r.cause || "") +
          "<br>Fix: " +
          escapeHtml(r.fix || "") +
          "</p>"
      )
      .join("");
    return (
      "<h3>" +
      summary.suite +
      " — " +
      summary.verdict +
      " (" +
      summary.passed +
      " passed / " +
      summary.failed +
      " failed)</h3><table><thead><tr><th>Result</th><th>Layer</th><th>Case</th><th>Detail</th></tr></thead><tbody>" +
      rows +
      "</tbody></table>" +
      rcas
    );
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function buildEmailHtml(suites) {
    const cluster = state.data.fixtures.cluster;
    const rca = state.data.rca_report || {};
    const fired = rca.fired || state.data.fixtures.rca.findings || [];
    const logs = podLogLines();
    const health =
      (cluster.pods || []).some((p) => p.status !== "Running" || !p.ready) ? "DEGRADED" : "HEALTHY";
    const podRows = (cluster.pods || [])
      .map((p) => {
        const live = current(p.component);
        return (
          "<tr><td>" +
          p.component +
          "</td><td>" +
          p.status +
          "</td><td>" +
          p.restarts +
          "</td><td>" +
          (p.last_reason || "—") +
          "</td><td>" +
          live.cpu.toFixed(1) +
          "%</td></tr>"
        );
      })
      .join("");
    const rcaHtml = fired
      .map(
        (f) =>
          "<p><strong>" +
          escapeHtml((f.id ? f.id + " · " : "") + (f.title || "")) +
          "</strong><br>Symptom: " +
          escapeHtml(f.observation || f.symptom || "") +
          "<br>Cause: " +
          escapeHtml(f.likely_cause || f.cause || "") +
          "<br>Fix: " +
          escapeHtml(f.fix || f.recommendation || "") +
          "</p>"
      )
      .join("");
    const suiteHtml = suites.map(suiteBlockHtml).join("");
    return (
      "<p>Simulated DataHub lab report. Cluster <code>" +
      escapeHtml(state.session.cluster || cluster.cluster) +
      "</code> · ns <code>" +
      escapeHtml(state.session.namespace || cluster.namespace) +
      "</code>. Verdict: <strong>" +
      health +
      "</strong>.</p>" +
      "<h3>Pod health</h3><table><thead><tr><th>Component</th><th>Status</th><th>Restarts</th><th>Last reason</th><th>CPU % limit</th></tr></thead><tbody>" +
      podRows +
      "</tbody></table>" +
      "<h3>Errors from pod logs (fixture)</h3><pre>" +
      escapeHtml(logs.join("\n") || "none") +
      "</pre>" +
      "<h3>RCA from those logs</h3>" +
      (rcaHtml || "<p>No fired rules.</p>") +
      suiteHtml +
      "<p style='color:#5c6675;font-size:12px'>Not a live cluster. No SMTP was used. Keyword/hybrid agent — a model did not invent these numbers.</p>"
    );
  }

  function emailSubject(suites) {
    const health = (state.data.fixtures.cluster.pods || []).some((p) => p.status !== "Running" || !p.ready)
      ? "DEGRADED"
      : "HEALTHY";
    const smoke = suites.find((s) => s.suite === "smoke");
    const fail = suites.some((s) => s.failed);
    return (
      "[DataHub lab] " +
      health +
      " · mae-consumer OOMKilled · smoke " +
      ((smoke && smoke.verdict) || "n/a") +
      (fail ? " · failures attached" : "")
    );
  }

  function appendEmailLog(line) {
    state.email.log.unshift(line);
    $("email-log").textContent = state.email.log.join("\n");
  }

  function sendEmailPreview() {
    if (!state.connected) return;
    const to = $("email-to").value.trim() || "sanket.dhamke@gmail.com";
    $("email-to-view").textContent = to;
    const suites = runEmailSuites();
    suites.forEach((summary) => renderSuitePanel(summary));
    const signature = issueSignature(suites);
    const hours = scheduleHours();
    const onIssue = $("email-on-issue").checked;
    const now = new Date();
    const next = new Date(now.getTime() + hours * 3600 * 1000);
    const already = state.email.signatures.indexOf(signature) !== -1;
    const html = buildEmailHtml(suites);
    $("email-subject").textContent = emailSubject(suites);
    $("email-body").innerHTML = html;
    showTab("email");
    if (already && onIssue) {
      appendEmailLog(
        now.toISOString() +
          "  deduped On new issue — signature already emailed. Waiting for every " +
          hours +
          "h schedule (next " +
          (state.email.nextAt || next.toISOString()) +
          "). Preview refreshed. To=" +
          to +
          " SMTP=none"
      );
      return;
    }
    state.email.signatures.push(signature);
    state.email.lastSent = now.toISOString();
    state.email.nextAt = next.toISOString();
    appendEmailLog(
      now.toISOString() +
        "  preview sent To=" +
        to +
        " signature=" +
        signature.split("|")[0] +
        " next=" +
        state.email.nextAt +
        " every=" +
        hours +
        "h onNewIssue=" +
        onIssue +
        " SMTP=none"
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
    document.querySelector(".tabs").addEventListener("click", (e) => {
      const tab = e.target.closest(".tab");
      if (tab) showTab(tab.dataset.tab);
    });
    ["f-pipeline", "f-host", "f-user", "f-db", "f-schema", "f-table"].forEach((id) => {
      $(id).addEventListener("input", syncYamlFromForm);
    });
    $("btn-starter").addEventListener("click", () => fillFormFromYaml(state.data.recipes.postgres));
    $("btn-submit").addEventListener("click", submitRecipe);
    $("btn-connect").addEventListener("click", () => {
      runConnect();
    });
    $("btn-email-preview").addEventListener("click", sendEmailPreview);
  }

  async function main() {
    const res = await fetch("js/demo-data.json");
    state.data = await res.json();
    bind();
  }

  window.LabConsole = { ask, state, runConnect, sendEmailPreview };
  main();
})();
