/* Vanilla JS port of agent/router.py + agent/executor.py. Python + tests are source of truth. */
(function (root) {
  function normalize(q) {
    return String(q || "").toLowerCase().split(/\s+/).join(" ");
  }

  function matchRule(question, rules) {
    const blob = normalize(question);
    const padded = " " + blob + " ";
    for (const rule of rules) {
      for (const token of rule.any) {
        const needle = token.toLowerCase();
        if (needle.startsWith(" ") || needle.endsWith(" ")) {
          if (padded.includes(needle)) return rule;
        } else if (blob.includes(needle)) {
          return rule;
        }
      }
    }
    return null;
  }

  function namedComponent(question) {
    const blob = question.toLowerCase();
    const aliases = [
      ["datahub-mae-consumer", ["datahub-mae-consumer", "mae-consumer", "mae consumer"]],
      ["datahub-mce-consumer", ["datahub-mce-consumer", "mce-consumer", "mce consumer"]],
      ["datahub-frontend", ["datahub-frontend", "frontend"]],
      ["datahub-actions", ["datahub-actions", "actions executor", "datahub actions"]],
      ["datahub-gms", ["datahub-gms", "gms"]],
    ];
    for (const [canonical, list] of aliases) {
      if (list.some((a) => blob.includes(a))) return canonical;
    }
    return null;
  }

  function caveat() {
    return "Keyword/rule router. Numbers come from checked-in fixtures, not a model. Fictional DataHub demo tenant — not a live cluster.";
  }

  function extractCredentials(question) {
    const u = String(question || "").match(/user(?:name)?(?:\s+as)?\s*[:=]?\s*['"]?([A-Za-z0-9._-]+)/i);
    const p = String(question || "").match(/pass(?:word)?(?:\s+as)?\s*[:=]?\s*['"]?([A-Za-z0-9._-]+)/i);
    return { username: u ? u[1] : null, password: p ? p[1] : null };
  }

  function parseTargets(question) {
    const found = [];
    const re = /10\s*(?:m|million)|10,000,000|10000000|1\s*(?:m|million)|1,000,000|1000000/gi;
    let m;
    while ((m = re.exec(question || ""))) {
      const token = m[0].replace(/[\s,]/g, "").toLowerCase();
      const n = token.startsWith("10") ? 10000000 : 1000000;
      if (!found.includes(n)) found.push(n);
    }
    return found;
  }

  function inferSuite(question) {
    const q = question.toLowerCase();
    let layer = null;
    if (/\bui\b/.test(q)) layer = "ui";
    else if (/\bapi\b/.test(q)) layer = "api";
    else if (q.includes("performance")) layer = "performance";
    let suite = null;
    if (q.includes("regression")) suite = "regression";
    else if (q.includes("sanity")) suite = "sanity";
    else if (q.includes("smoke")) suite = "smoke";
    return { suite, layer };
  }

  function inferApi(question) {
    const q = question.toLowerCase();
    if (["alert", "incident"].some((w) => q.includes(w))) return "graphql.listIncidents";
    if (q.includes("log in") || q.includes("login")) return "rest.logIn";
    if (q.includes("/health") || q.includes("gms health") || q.includes("health api")) return "rest.health";
    if (q.includes("list ingestion") || q.includes("list sources")) return "graphql.listIngestionSources";
    if (q.includes("searchacross") || q.includes("search datasets")) return "graphql.searchAcrossEntities";
    return null;
  }

  function formatRca(rca, heading) {
    const title = heading || rca.name || rca.id || "Failure";
    const evidence = (rca.evidence || []).map((e) => "  - " + e).join("\n");
    return (
      "RCA — " +
      title +
      "\nSymptom: " +
      rca.symptom +
      "\nEvidence:\n" +
      evidence +
      "\nCause: " +
      rca.cause +
      "\nFix: " +
      rca.fix
    );
  }

  function summarizeCases(cases, suite, layer) {
    const passed = cases.filter((c) => c.status === "pass");
    const failed = cases.filter((c) => c.status === "fail");
    const rcas = failed.filter((c) => c.rca).map((c) => Object.assign({ id: c.id, name: c.name }, c.rca));
    return {
      suite,
      layer: layer || null,
      total: cases.length,
      passed: passed.length,
      failed: failed.length,
      skipped: cases.length - passed.length - failed.length,
      duration_ms: cases.reduce((n, c) => n + (c.duration_ms || 0), 0),
      failed_ids: failed.map((c) => c.id),
      rcas,
      cases,
      verdict: failed.length ? "FAIL" : "PASS",
    };
  }

  function runSuite(data, suite, layer) {
    const rows = (((data.fixtures || {}).suites || {}).cases) || [];
    let cases = rows.filter((c) => (c.suites || []).includes(suite));
    if (layer) cases = cases.filter((c) => c.layer === layer);
    return summarizeCases(cases, suite, layer);
  }

  function formatSuite(summary) {
    const layer = summary.layer || "api+ui+performance";
    const lines = [
      "Suite `" +
        summary.suite +
        "` layer=" +
        layer +
        " → " +
        summary.verdict +
        " (" +
        summary.passed +
        " passed, " +
        summary.failed +
        " failed, " +
        summary.total +
        " total, " +
        summary.duration_ms +
        " ms).",
      "This is a replay of the checked-in suite catalog — the same smoke/sanity/regression markers as pytest. GitHub Pages does not spawn pytest.",
    ];
    (summary.cases || []).forEach((c) => {
      const mark = c.status === "pass" ? "PASS" : "FAIL";
      lines.push("- [" + mark + "] " + c.layer + " " + c.id + ": " + c.name + " (" + c.duration_ms + " ms)");
      if (c.status === "fail") {
        lines.push("    expected: " + c.expected);
        lines.push("    actual:   " + c.actual);
      }
    });
    (summary.rcas || []).forEach((rca) => {
      lines.push("");
      lines.push(formatRca(rca, rca.name));
    });
    return lines.join("\n");
  }

  function login(data, username, password) {
    const accounts = (((data.fixtures || {}).users || {}).accounts) || [];
    if (!username || !password) {
      return {
        ok: false,
        status: 400,
        path: "/logIn",
        method: "POST",
        error: "username and password are required. This lab will not invent credentials.",
        body: null,
      };
    }
    const row = accounts.find((a) => a.username === username);
    if (!row || row.password !== password) {
      return {
        ok: false,
        status: 401,
        path: "/logIn",
        method: "POST",
        username,
        error: "invalid credentials",
        body: { message: "Unauthorized", username },
      };
    }
    return {
      ok: true,
      status: 200,
      path: "/logIn",
      method: "POST",
      username,
      body: {
        actor: row.urn,
        displayName: row.displayName,
        role: row.role,
        session: "PLAY_SESSION=lab-mock",
      },
    };
  }

  function runApi(data, endpointId, params) {
    params = params || {};
    if (endpointId === "rest.logIn") {
      const run = login(data, params.username, params.password);
      run.endpoint = endpointId;
      return run;
    }
    if (endpointId === "rest.health") {
      return {
        ok: true,
        status: 200,
        method: "GET",
        path: "/health",
        endpoint: endpointId,
        body: { ok: true, component: "datahub-gms", mode: "lab-mock" },
      };
    }
    if (endpointId === "graphql.listIncidents") {
      const alerts = data.fixtures.alerts;
      return {
        ok: true,
        status: 200,
        method: "POST",
        path: "/api/graphql",
        endpoint: endpointId,
        body: {
          open: alerts.open,
          total: alerts.total,
          resolved: alerts.resolved,
          incidents: alerts.items
            .filter((i) => i.state === "ACTIVE")
            .map((i) => ({
              urn: i.urn,
              title: i.title,
              state: i.state,
              severity: i.severity,
              entity: i.entity,
            })),
        },
      };
    }
    if (endpointId === "graphql.listIngestionSources") {
      const bundle = data.fixtures.ingestion;
      return {
        ok: true,
        status: 200,
        method: "POST",
        path: "/api/graphql",
        endpoint: endpointId,
        body: {
          total: bundle.sources.length,
          sources: bundle.sources.map((s) => ({ name: s.name, type: s.type, assets: s.assets })),
        },
      };
    }
    if (endpointId === "graphql.searchAcrossEntities") {
      return {
        ok: true,
        status: 200,
        method: "POST",
        path: "/api/graphql",
        endpoint: endpointId,
        body: data.fixtures.ingestion.totals,
      };
    }
    return { ok: false, status: 404, endpoint: endpointId, error: "no executable mock", body: null };
  }

  function podStatus(data) {
    const cluster = data.fixtures.cluster;
    const rca = data.fixtures.rca;
    const pods = cluster.pods;
    const unhealthy = pods.filter((p) => p.status !== "Running" || !p.ready);
    const oom = pods.filter((p) => String(p.last_reason || "").toLowerCase().includes("oom"));
    const lines = [
      "Namespace `" + cluster.namespace + "` on `" + cluster.cluster + "` (" + cluster.note + "). Snapshot `" + cluster.generated_at + "`.",
      unhealthy.length + " of " + pods.length + " pods are not ready:",
    ];
    unhealthy.forEach((pod) => {
      lines.push(
        "- `" + pod.name + "` (" + pod.component + "): status=" + pod.status + ", restarts=" + pod.restarts + ", last_reason=" + (pod.last_reason || "-") + ", probe=" + (pod.probe || "-")
      );
    });
    if (oom.length) {
      lines.push("OOMKilled in this fixture: " + oom.map((p) => "`" + p.component + "`").join(", ") + ".");
    }
    if (data.rca_report && data.rca_report.principle) {
      lines.push(data.rca_report.principle);
    }
    lines.push("Root-cause notes from the RCA fixture:");
    rca.findings.forEach((f) => lines.push("- [" + f.severity + "] " + f.component + ": " + f.title));
    return {
      route: "pod_status",
      source: "handler:pod_status",
      tools: ["read_fixture:agent/fixtures/cluster.json", "read_fixture:agent/fixtures/rca.json"],
      answer: lines.join("\n"),
      metrics: { crashing_pods: unhealthy.length, oomkilled: oom.length, pod_count: pods.length },
      citations: ["agent/fixtures/cluster.json"],
      ui: "highlight_pods",
      caveat: caveat(),
    };
  }

  function resourceMetrics(data, question) {
    const payload = data.fixtures.metrics;
    const named = namedComponent(question);
    let selected = named ? payload.workers.filter((w) => w.component === named) : payload.workers.slice();
    if (!selected.length) selected = payload.workers.slice();
    const lines = [
      "Simulated " + payload.window + " window from `" + payload.generated_at + "` (" + payload.note + ").",
      "CPU and memory percentages are of each pod's configured limit, not of node capacity. A pod at 95% of a tiny limit can still be idle in millicores. If a pod has no limit, no percentage is computed.",
    ];
    if (named) lines.push("Filter: `" + named + "`.");
    selected.forEach((row) => {
      const limit = row.memory_limit_mib || 0;
      const cpuBit =
        row.cpu_pct != null ? "CPU " + row.cpu_pct + "% of its limit" : "CPU (no limit — no percentage)";
      let memBit;
      if (limit) {
        const memPct = ((100 * row.memory_mib) / limit).toFixed(1);
        memBit = "memory " + row.memory_mib + " MiB / " + limit + " MiB (" + memPct + "% of limit)";
      } else {
        memBit = "memory " + row.memory_mib + " MiB (no limit — no percentage)";
      }
      lines.push("- `" + row.component + "` (`" + row.pod + "`): " + cpuBit + " · " + memBit);
    });
    const hottest = selected.reduce((a, b) => (a.cpu_pct > b.cpu_pct ? a : b));
    lines.push(
      "Highest CPU in this selection: `" + hottest.component + "` at " + hottest.cpu_pct + "% of its pod limit."
    );
    return {
      route: "resource_metrics",
      source: "handler:resource_metrics",
      tools: ["read_fixture:agent/fixtures/metrics.json"],
      answer: lines.join("\n"),
      metrics: { filter: named, workers: selected, highest_cpu_pct: hottest.cpu_pct },
      citations: ["agent/fixtures/metrics.json"],
      ui: "highlight_metrics",
      caveat: caveat(),
    };
  }

  function ingestionAssets(data) {
    const bundle = data.fixtures.ingestion;
    const lines = [
      "Ingestion sources on fictional tenant `" + bundle.tenant + "` (" + bundle.note + "). Snapshot `" + bundle.generated_at + "`.",
    ];
    bundle.sources.forEach((src) => {
      const extra = src.database ? "database=" + src.database : "service_name=" + src.service_name;
      lines.push(
        "- `" + src.name + "` type=" + src.type + " pipeline=`" + src.pipeline_name + "` urn=`" + src.urn + "` assets=" + src.assets + " last_run=" + src.last_run_status
      );
      lines.push("  host_port=" + src.host_port + " " + extra);
    });
    const t = bundle.totals;
    lines.push(
      "Total assets in this fixture: " + t.assets + " (datasets=" + t.datasets + ", containers=" + t.containers + ", dataJobs=" + t.dataJobs + ", lineage_edges=" + t.lineage_edges + ")."
    );
    return {
      route: "ingestion_assets",
      source: "handler:ingestion_assets",
      tools: ["read_fixture:agent/fixtures/ingestion.json"],
      answer: lines.join("\n"),
      metrics: Object.assign({ postgres_assets: 86, oracle_assets: 54, total_assets: t.assets }, t),
      citations: ["agent/fixtures/ingestion.json"],
      ui: "highlight_sources",
      caveat: caveat(),
    };
  }

  function ingestRecipe(data) {
    const recipe = data.recipes.postgres;
    return {
      route: "ingest_recipe",
      source: "handler:ingest_recipe",
      tools: ["read_recipe:agent/recipes/postgres.yml"],
      answer:
        "I will not invent a postgres recipe. Fill the starter YAML (DataHub `type: postgres` shape: host_port, username, database, schema_pattern / table_pattern allow lists, sink datahub-rest → datahub-gms). On submit this lab simulates GraphQL `createIngestionSource` then `createIngestionExecutionRequest`, returns a run id, and plays a fake execution while CPU/memory for `datahub-actions` and `datahub-gms` tick.\n\n```yaml\n" +
        recipe.trim() +
        "\n```",
      metrics: null,
      citations: ["agent/recipes/postgres.yml"],
      ui: "recipe_editor",
      recipe,
      caveat: caveat(),
    };
  }

  function tokens(text) {
    return new Set((String(text).toLowerCase().match(/[a-z0-9]+/g) || []));
  }

  function score(question, entry) {
    const q = question.toLowerCase();
    let n = 0;
    (entry.keywords || []).forEach((kw) => {
      if (q.includes(kw.toLowerCase())) n += 4;
    });
    const hay = tokens(
      [entry.id, entry.title, entry.method, entry.path, entry.summary, (entry.keywords || []).join(" ")].join(" ")
    );
    tokens(question).forEach((t) => {
      if (hay.has(t)) n += 1;
    });
    if (q.includes("create") && entry.method === "POST" && (entry.id || "").includes("create")) n += 3;
    if (q.includes("ingestion") && (entry.id || "").includes("Ingestion")) n += 2;
    return n;
  }

  function kbRetrieve(data, question) {
    const ranked = data.endpoints
      .map((entry) => [score(question, entry), entry])
      .sort((a, b) => b[0] - a[0]);
    const bestScore = ranked[0][0];
    const best = ranked[0][1];
    if (bestScore <= 0) {
      return {
        route: "kb_retrieve",
        source: "kb:none",
        tools: ["kb_search:agent/kb/endpoints.json"],
        answer: "The catalog has no matching GraphQL/REST entry. No number was generated.",
        metrics: null,
        ui: null,
        caveat: caveat(),
      };
    }
    return {
      route: "kb_retrieve",
      source: "kb:" + best.id,
      tools: ["kb_search:agent/kb/endpoints.json", "read_doc:" + best.citation],
      answer: best.method + " `" + best.path + "` — " + best.title + ".\n" + best.summary + "\nCitation: `" + best.citation + "`.",
      metrics: null,
      citations: [best.citation],
      match: { id: best.id, method: best.method, path: best.path, score: bestScore },
      ui: null,
      caveat: caveat(),
    };
  }

  function annotateSource(result) {
    const source = String((result && result.source) || "");
    const routeName = String((result && result.route) || "");
    let kind = "handler";
    let label = "Handler · fixtures only";
    if (source.indexOf("kb:") === 0 || routeName === "kb_retrieve") {
      kind = "kb";
      label = "Knowledge base · cited catalog";
    } else if (routeName === "run_suite" || source.indexOf("handler:run_suite") === 0) {
      kind = "suite";
      label = "Suite catalog · pytest markers";
    } else if (source.indexOf("fallback") === 0 || routeName === "fallback") {
      kind = "fallback";
      label = "Fallback · no match";
    }
    result.source_kind = kind;
    result.source_label = label;
    return result;
  }

  function formatEngineReport(report) {
    if (!report) return "No RCA report in this demo payload.";
    const lines = [
      "Deterministic RCA — rules first. No model chose a tool or a number.",
      report.principle || "",
      "",
      "Fired (" + (report.fired || []).length + "):",
    ];
    (report.fired || []).forEach((row) => {
      lines.push("[" + row.severity + "] " + row.id + " · " + row.component + " — " + row.title);
      lines.push("  Observation: " + row.observation);
      (row.evidence || []).forEach((item) => lines.push("    - " + item));
      lines.push("  Cause: " + row.cause);
      lines.push("  Fix: " + row.recommendation);
      lines.push("");
    });
    lines.push("Evaluated, not fired (this is part of the diagnosis):");
    (report.skipped || []).forEach((row) => {
      lines.push("- " + row.id + ": " + row.why);
    });
    return lines.join("\n").trim();
  }

  function toolCatalog(data) {
    const bundle = ((data.fixtures || {}).tools) || { tools: [] };
    const tools = bundle.tools || [];
    const cluster = tools.filter((row) => !row.gms);
    const gms = tools.filter((row) => row.gms);
    const lines = [
      "Lab tool catalog — " +
        tools.length +
        " tools. The keyword table chooses which one runs. A model never picks a tool and never invents a number.",
      bundle.note || "",
      "",
      "Cluster / fixture tools (no GraphQL):",
    ];
    cluster.forEach((row) => {
      lines.push("- `" + row.id + "` — " + row.returns + " (reads " + row.needs + ")");
    });
    lines.push("");
    lines.push("GMS GraphQL tools (need the metadata fixture, not a live cluster URL):");
    gms.forEach((row) => {
      lines.push("- `" + row.id + "` — " + row.returns + " (reads " + row.needs + ")");
    });
    lines.push("");
    lines.push(
      "`gms_heap` reads datahub-gms java opts from the cluster fixture. It does not query GMS GraphQL. CPU/memory percentages are of each pod's own limit, not node capacity."
    );
    return {
      route: "tool_catalog",
      source: "handler:tool_catalog",
      tools: ["read_fixture:agent/fixtures/tools.json"],
      answer: lines.join("\n"),
      metrics: {
        tool_count: tools.length,
        gms_tools: gms.map((row) => row.id),
        cluster_tools: cluster.map((row) => row.id),
      },
      ui: "tools",
      catalog: bundle,
      caveat: caveat(),
    };
  }

  function perfRca(data) {
    const report = data.rca_report || { fired: [], skipped: [], principle: "", counts: {} };
    return {
      route: "perf_rca",
      source: "handler:perf_rca",
      tools: ["rule_rca:agent/rca_engine.py", "read_fixture:agent/fixtures/cluster.json"],
      answer: formatEngineReport(report),
      metrics: {
        fired: (report.fired || []).map((row) => row.id),
        skipped: (report.skipped || []).map((row) => row.id),
        counts: report.counts || {},
        unhealthy: report.unhealthy,
      },
      ui: "rca",
      rca: report,
      caveat: caveat(),
    };
  }

  function fallback() {
    return {
      route: "fallback",
      source: "fallback:deterministic",
      tools: [],
      answer:
        "No handler or catalog entry matched that question. This sample does not call a language model, so it will not invent pod counts, CPU, or asset totals. Try: crashing/OOM pods, CPU of datahub-gms, how many assets, how many alerts, login with emuser/empass, run API sanity, check UI sanity, current state of the application, list the lab tools, or what config to upgrade for 1M / 10M assets.",
      metrics: null,
      ui: null,
      caveat: caveat(),
    };
  }

  function loginApi(data, question) {
    const creds = extractCredentials(question);
    const run = login(data, creds.username, creds.password);
    if (!creds.username || !creds.password) {
      return {
        route: "login_api",
        source: "handler:login_api",
        tools: ["kb:rest.logIn"],
        answer:
          "POST `/logIn` is in the catalog, but this lab will not invent credentials. Say: test the login with username as emuser and password as empass (fictional lab user).",
        metrics: { status: 400, ok: false },
        ui: "api_result",
        api: run,
        caveat: caveat(),
      };
    }
    let answer;
    if (run.ok) {
      answer =
        "POST `/logIn` → " +
        run.status +
        " OK.\nActor `" +
        run.body.actor +
        "` (" +
        run.body.displayName +
        ", " +
        run.body.role +
        ").\nSession cookie: `" +
        run.body.session +
        "`.\nFictional lab user only.";
    } else {
      answer =
        "POST `/logIn` username=`" +
        creds.username +
        "` → " +
        run.status +
        " " +
        run.error +
        ".\nRCA — login rejected\nSymptom: UI/API session was not created.\nEvidence: mock GMS compared the payload to agent/fixtures/users.json.\nCause: username missing from the lab roster, or password did not match.\nFix: use the documented lab pair emuser / empass. Do not retry with invented users.";
    }
    return {
      route: "login_api",
      source: "handler:login_api",
      tools: ["http:POST /logIn", "read_fixture:agent/fixtures/users.json"],
      answer,
      metrics: { ok: run.ok, status: run.status, username: creds.username },
      ui: "api_result",
      api: run,
      caveat: caveat(),
    };
  }

  function runNamedSuite(data, question, suite, layer) {
    if (!suite) {
      const inferred = inferSuite(question);
      suite = inferred.suite;
      layer = inferred.layer;
    }
    if (!suite && layer) suite = "sanity";
    if (!suite) return fallback();
    const summary = runSuite(data, suite, layer || null);
    return {
      route: "run_suite",
      source: "handler:run_suite:" + suite + (layer ? ":" + layer : ""),
      tools: ["read_fixture:agent/fixtures/suites.json"],
      answer: formatSuite(summary),
      metrics: {
        suite,
        layer: layer || null,
        passed: summary.passed,
        failed: summary.failed,
        total: summary.total,
        verdict: summary.verdict,
        failed_ids: summary.failed_ids,
      },
      ui: "suite_report",
      report: summary,
      session_update: { awaiting_regression: false },
      awaiting_regression: false,
      caveat: caveat(),
    };
  }

  function executeApi(data, question) {
    const endpointId = inferApi(question);
    if (endpointId === "rest.logIn") return loginApi(data, question);
    if (!endpointId) return fallback();
    const run = runApi(data, endpointId);
    let answer;
    let metrics;
    if (endpointId === "graphql.listIncidents" && run.body) {
      const lines = [
        "POST `/api/graphql` listIncidents (DataHub incidents; the lab maps “alerts” here).",
        "Open: " + run.body.open + " · resolved: " + run.body.resolved + " · total: " + run.body.total + ".",
      ];
      (run.body.incidents || []).forEach((item) => {
        lines.push("- [" + item.severity + "] " + item.title + " (" + item.entity + ")");
      });
      answer = lines.join("\n");
      metrics = { open: run.body.open, total: run.body.total };
    } else {
      answer = (run.method || "") + " `" + (run.path || "") + "` → " + run.status + ".\n" + JSON.stringify(run.body, null, 2);
      metrics = { status: run.status, ok: run.ok };
    }
    return {
      route: "execute_api",
      source: "handler:execute_api:" + endpointId,
      tools: ["kb_exec:" + endpointId],
      answer,
      metrics,
      ui: "api_result",
      api: run,
      caveat: caveat(),
    };
  }

  function appStatus(data) {
    const cluster = data.fixtures.cluster;
    const rca = data.fixtures.rca;
    const alerts = data.fixtures.alerts;
    const pods = cluster.pods;
    const unhealthy = pods.filter((p) => p.status !== "Running" || !p.ready);
    const smoke = runSuite(data, "smoke", null);
    const sanity = runSuite(data, "sanity", null);
    const health = unhealthy.length || sanity.failed || smoke.failed ? "DEGRADED" : "HEALTHY";
    const lines = [
      "Application verdict: " + health + " on `" + cluster.cluster + "` ns `" + cluster.namespace + "` (simulated).",
      "Pods: " + unhealthy.length + " / " + pods.length + " not ready (" + (unhealthy.map((p) => p.component).join(", ") || "none") + ").",
      "Open DataHub incidents (alerts): " + alerts.open + ". Assets: " + data.fixtures.ingestion.totals.assets + ".",
      "Root cause (from fixtures):",
    ];
    const fired = ((data.rca_report || {}).fired || []).length
      ? data.rca_report.fired
      : rca.findings;
    fired.forEach((f) =>
      lines.push("- " + f.severity + " " + (f.id ? f.id + " " : "") + (f.component || "") + ": " + f.title)
    );
    lines.push(
      "Auto-ran smoke: " + smoke.verdict + " " + smoke.passed + "/" + smoke.total + " and sanity: " + sanity.verdict + " " + sanity.passed + "/" + sanity.total + "."
    );
    if (sanity.rcas && sanity.rcas[0]) {
      lines.push("");
      lines.push(formatRca(sanity.rcas[0], sanity.rcas[0].name));
    }
    lines.push("");
    lines.push("Full regression is heavier (API + UI + performance, including lineage and MAE memory). Say yes to run it, or no to stop here.");
    return {
      route: "app_status",
      source: "handler:app_status",
      tools: ["run_suite:smoke", "run_suite:sanity"],
      answer: lines.join("\n"),
      metrics: {
        health,
        unhealthy: unhealthy.length,
        open_incidents: alerts.open,
        assets: data.fixtures.ingestion.totals.assets,
        smoke_verdict: smoke.verdict,
        sanity_verdict: sanity.verdict,
      },
      ui: "verdict",
      awaiting_regression: true,
      session_update: { awaiting_regression: true },
      health: { smoke_report: smoke, sanity_report: sanity, health },
      caveat: caveat(),
    };
  }

  function skipRegression() {
    return {
      route: "skip_regression",
      source: "handler:app_status",
      tools: [],
      answer:
        "Regression skipped. Current quality verdict stays at the smoke + sanity read: application is DEGRADED until datahub-mae-consumer is off OOMKilled and UI search/lineage are green.",
      metrics: { regression: "skipped" },
      ui: "verdict",
      awaiting_regression: false,
      session_update: { awaiting_regression: false },
      caveat: caveat(),
    };
  }

  function capacityPlan(data, question) {
    const cfg = data.fixtures.app_config;
    let targets = parseTargets(question);
    if (!targets.length) targets = [1000000, 10000000];
    const plans = targets
      .map((n) => {
        const block = cfg.targets[String(n)];
        return block ? Object.assign({ assets: n }, block) : null;
      })
      .filter(Boolean);
    const lines = [
      "Current ingested assets in this fixture: " + cfg.current_assets + " (postgres 86 + oracle 54).",
      "Blockers before any scale-up:",
    ];
    (cfg.blockers || []).forEach((b) => lines.push("- " + b));
    plans.forEach((block) => {
      lines.push("");
      lines.push("To ingest " + block.label + " (" + block.scale_vs_current + "):");
      (block.changes || []).forEach((change) => {
        lines.push("- `" + change.component + "`: " + change.from + " → " + change.to);
        lines.push("  why: " + change.why);
      });
    });
    return {
      route: "capacity_plan",
      source: "handler:capacity_plan",
      tools: ["read_fixture:agent/fixtures/app_config.json"],
      answer: lines.join("\n"),
      metrics: { current_assets: cfg.current_assets, targets: plans.map((p) => p.assets) },
      ui: "capacity",
      capacity: { current_assets: cfg.current_assets, current: cfg.current, blockers: cfg.blockers, plans },
      caveat: caveat(),
    };
  }

  const YES = /^\s*(y|yes|yeah|yep|ok|okay|sure|do it|go ahead|please run|run it|run them|run regression)\b/i;
  const NO = /^\s*(n|no|nope|skip|not now|later|don't|dont)\b/i;

  const HANDLERS = {
    login_api: loginApi,
    run_suite: runNamedSuite,
    app_status: appStatus,
    capacity_plan: capacityPlan,
    execute_api: executeApi,
    ingest_recipe: ingestRecipe,
    pod_status: podStatus,
    resource_metrics: resourceMetrics,
    ingestion_assets: ingestionAssets,
    kb_retrieve: kbRetrieve,
    perf_rca: perfRca,
    tool_catalog: toolCatalog,
  };

  function route(data, question, session) {
    const text = String(question || "").trim();
    session = session || {};
    if (session.awaiting_regression && text) {
      if (YES.test(text)) {
        return annotateSource(
          Object.assign(runNamedSuite(data, text, "regression", null), {
            question: text,
            model_available: false,
          })
        );
      }
      if (NO.test(text)) {
        return annotateSource(
          Object.assign(skipRegression(), { question: text, model_available: false })
        );
      }
    }
    if (!text) {
      const empty = fallback();
      empty.question = "";
      return annotateSource(empty);
    }
    const rule = matchRule(text, data.rules);
    let result;
    if (!rule) result = fallback();
    else if (HANDLERS[rule.route]) result = HANDLERS[rule.route](data, text);
    else result = fallback();
    result.question = text;
    result.model_available = false;
    return annotateSource(result);
  }

  root.LabRouter = { route, namedComponent, runSuite };
})(window);
