/* Vanilla JS port of agent/router.py. Python + tests are the source of truth. */
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

  function podStatus(data, question) {
    const cluster = data.fixtures.cluster;
    const rca = data.fixtures.rca;
    const pods = cluster.pods;
    const unhealthy = pods.filter((p) => p.status !== "Running" || !p.ready);
    const oom = pods.filter((p) => String(p.last_reason || "").toLowerCase().includes("oom"));
    const lines = [
      `Namespace \`${cluster.namespace}\` on \`${cluster.cluster}\` (${cluster.note}). Snapshot \`${cluster.generated_at}\`.`,
      `${unhealthy.length} of ${pods.length} pods are not ready:`,
    ];
    unhealthy.forEach((pod) => {
      lines.push(
        `- \`${pod.name}\` (${pod.component}): status=${pod.status}, restarts=${pod.restarts}, last_reason=${pod.last_reason || "-"}, probe=${pod.probe || "-"}`
      );
    });
    if (oom.length) {
      lines.push("OOMKilled in this fixture: " + oom.map((p) => "`" + p.component + "`").join(", ") + ".");
    }
    lines.push("Root-cause notes from the RCA fixture:");
    rca.findings.forEach((f) => lines.push(`- [${f.severity}] ${f.component}: ${f.title}`));
    return {
      route: "pod_status",
      source: "handler:pod_status",
      tools: ["read_fixture:agent/fixtures/cluster.json", "read_fixture:agent/fixtures/rca.json"],
      answer: lines.join("\n"),
      metrics: {
        crashing_pods: unhealthy.length,
        oomkilled: oom.length,
        pod_count: pods.length,
      },
      citations: ["agent/fixtures/cluster.json"],
      ui: "highlight_pods",
      caveat: caveat(),
    };
  }

  function resourceMetrics(data, question) {
    const payload = data.fixtures.metrics;
    const named = namedComponent(question);
    let selected = named
      ? payload.workers.filter((w) => w.component === named)
      : payload.workers.slice();
    if (!selected.length) selected = payload.workers.slice();
    const lines = [
      `Simulated ${payload.window} window from \`${payload.generated_at}\` (${payload.note}).`,
    ];
    if (named) lines.push(`Filter: \`${named}\`.`);
    selected.forEach((row) => {
      const memPct = ((100 * row.memory_mib) / row.memory_limit_mib).toFixed(1);
      lines.push(
        `- \`${row.component}\` (\`${row.pod}\`): CPU ${row.cpu_pct}% · memory ${row.memory_mib} MiB / ${row.memory_limit_mib} MiB (${memPct}%)`
      );
    });
    const hottest = selected.reduce((a, b) => (a.cpu_pct > b.cpu_pct ? a : b));
    lines.push(`Highest CPU in this selection: \`${hottest.component}\` at ${hottest.cpu_pct}%.`);
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
      `Ingestion sources on fictional tenant \`${bundle.tenant}\` (${bundle.note}). Snapshot \`${bundle.generated_at}\`.`,
    ];
    bundle.sources.forEach((src) => {
      const extra = src.database ? `database=${src.database}` : `service_name=${src.service_name}`;
      lines.push(
        `- \`${src.name}\` type=${src.type} pipeline=\`${src.pipeline_name}\` urn=\`${src.urn}\` assets=${src.assets} last_run=${src.last_run_status}`
      );
      lines.push(`  host_port=${src.host_port} ${extra}`);
    });
    const t = bundle.totals;
    lines.push(
      `Total assets in this fixture: ${t.assets} (datasets=${t.datasets}, containers=${t.containers}, dataJobs=${t.dataJobs}, lineage_edges=${t.lineage_edges}).`
    );
    return {
      route: "ingestion_assets",
      source: "handler:ingestion_assets",
      tools: ["read_fixture:agent/fixtures/ingestion.json"],
      answer: lines.join("\n"),
      metrics: t,
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
      answer:
        `${best.method} \`${best.path}\` — ${best.title}.\n${best.summary}\nCitation: \`${best.citation}\`.`,
      metrics: null,
      citations: [best.citation],
      match: { id: best.id, method: best.method, path: best.path, score: bestScore },
      ui: null,
      caveat: caveat(),
    };
  }

  function fallback() {
    return {
      route: "fallback",
      source: "fallback:deterministic",
      tools: [],
      answer:
        "No handler or catalog entry matched that question. This sample does not call a language model, so it will not invent pod counts, CPU, or asset totals. Try: crashing/OOM pods, CPU of datahub-gms, postgres/oracle sources and total assets, ingest a postgres source, or which GraphQL mutation creates an ingestion source.",
      metrics: null,
      ui: null,
      caveat: caveat(),
    };
  }

  function route(data, question) {
    const text = String(question || "").trim();
    if (!text) {
      const empty = fallback();
      empty.question = "";
      return empty;
    }
    const rule = matchRule(text, data.rules);
    let result;
    if (!rule) result = fallback();
    else if (rule.route === "pod_status") result = podStatus(data, text);
    else if (rule.route === "resource_metrics") result = resourceMetrics(data, text);
    else if (rule.route === "ingestion_assets") result = ingestionAssets(data, text);
    else if (rule.route === "ingest_recipe") result = ingestRecipe(data, text);
    else if (rule.route === "kb_retrieve") result = kbRetrieve(data, text);
    else result = fallback();
    result.question = text;
    result.model_available = false;
    return result;
  }

  root.LabRouter = { route, namedComponent };
})(window);
