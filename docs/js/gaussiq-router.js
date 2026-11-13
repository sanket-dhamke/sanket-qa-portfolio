/* Vanilla JS port of gaussiq/router.py. Python + tests are source of truth. */
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

  function caveat() {
    return "Keyword/rule router. Numbers come from checked-in fixtures, not a model. Fictional GaussIQ 1.0 demo tenant — not a live product. Not affiliated with GaussIQ.";
  }

  function extractCredentials(question) {
    const u = String(question || "").match(/user(?:name)?(?:\s+as)?\s*[:=]?\s*['"]?([A-Za-z0-9._-]+)/i);
    const p = String(question || "").match(/pass(?:word)?(?:\s+as)?\s*[:=]?\s*['"]?([A-Za-z0-9._-]+)/i);
    return { username: u ? u[1] : null, password: p ? p[1] : null };
  }

  function inferSuite(question) {
    const q = question.toLowerCase();
    let layer = null;
    if (/\bui\b/.test(q)) layer = "ui";
    else if (/\bapi\b/.test(q)) layer = "api";
    else if (q.includes("performance")) layer = "performance";
    else if (q.includes("security")) layer = "security";
    let suite = null;
    if (q.includes("regression")) suite = "regression";
    else if (q.includes("sanity")) suite = "sanity";
    else if (q.includes("smoke")) suite = "smoke";
    return { suite, layer };
  }

  function runSuite(data, suite, layer) {
    const rows = (((data.fixtures || {}).suites || {}).cases) || [];
    let cases = rows.filter((c) => (c.suites || []).includes(suite));
    if (layer) cases = cases.filter((c) => c.layer === layer);
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

  function plainFailWhy(c) {
    const rca = (c && c.rca) || {};
    const blob = [rca.id, rca.symptom, rca.cause, c && c.actual].filter(Boolean).join(" ");
    if (blob.indexOf("AUTH-OPEN") !== -1) return "Case Intelligence API does not require login (AUTH-OPEN)";
    if (blob.indexOf("SECRET-IN-LOG") !== -1) return "Authorization header echoed in rec-engine logs (redacted)";
    if (blob.indexOf("CERT-MISMATCH") !== -1) return "AJ18991 HTTP 500 is a certificate SAN mismatch (CERT-MISMATCH)";
    if (blob.indexOf("CONNECTOR-LAG") !== -1) {
      return "signal-connector is crash-looping, so evidence is stale (CONNECTOR-LAG)";
    }
    const text = rca.symptom || rca.cause || (c && c.actual) || "failed";
    return String(text).split(".")[0].trim();
  }

  function formatSuite(summary) {
    const suite = (summary && summary.suite) || "suite";
    const layer = summary && summary.layer;
    let prefix = "";
    if (layer === "api") prefix = "API ";
    else if (layer === "security") prefix = "Security ";
    else if (layer === "performance") prefix = "Performance ";
    const failed = (summary && summary.failed) || 0;
    const verb = failed === 0 ? "passed" : "failed";
    const ms = Number((summary && summary.duration_ms) || 0);
    const approx = ms >= 50 ? "~" + Math.round(ms / 10) * 10 + " ms" : ms + " ms";
    const headline =
      prefix + suite + " " + verb + " (" + ((summary && summary.passed) || 0) + "/" + ((summary && summary.total) || 0) + ") in " + approx;
    const lines = [headline, ""];
    const cases = (summary && summary.cases) || [];
    const fails = cases.filter((c) => c.status === "fail");
    if (fails.length) {
      lines.push(fails.length === 1 ? "1 failed:" : fails.length + " failed:");
      fails.forEach((row) => lines.push("- " + (row.name || row.id) + " — " + plainFailWhy(row)));
    } else {
      cases.forEach((row) => lines.push("- " + (row.name || row.id)));
    }
    lines.push("");
    lines.push("Catalog replay — not a live pytest run.");
    return lines.join("\n");
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
      lines.push("  Symptom: " + row.observation);
      (row.evidence || []).forEach((item) => lines.push("    - " + item));
      lines.push("  Cause: " + row.cause);
      lines.push("  Fix: " + row.recommendation);
      lines.push("");
    });
    lines.push(report.skipped_heading || "Checked — not the cause");
    (report.skipped || []).forEach((row) => lines.push("- " + row.id + ": " + row.why));
    return lines.join("\n").trim();
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

  function computeAppHealth(data, opts) {
    opts = opts || {};
    const services = (((data || {}).fixtures || {}).services || {}).services || [];
    const report = (data && data.rca_report) || { fired: [] };
    const lastSmoke = opts.lastSmoke !== undefined ? opts.lastSmoke : runSuite(data, "smoke", null);
    const lastSanity = opts.lastSanity;
    const reasons = [];
    const crashloop = services.some((s) => /crashloop/i.test(s.status || ""));
    const smokeFail = !!(lastSmoke && lastSmoke.verdict === "FAIL");
    const sanityFail = !!(lastSanity && lastSanity.verdict === "FAIL");
    const fired = report.fired || [];
    const highRca = fired.some((f) => {
      const sev = String(f.severity || "").toUpperCase();
      return sev === "CRITICAL" || sev === "HIGH";
    });
    const authOpen = ((((data || {}).security_report || {}).fired) || []).some((f) => f.id === "AUTH-OPEN");
    const notReady = services.some((s) => !s.ready || s.status !== "Running");
    const restarts = services.some((s) => Number(s.restarts || 0) > 0);
    const allRunning = services.length > 0 && services.every((s) => s.status === "Running" && s.ready);
    const smokePassed = !!(lastSmoke && lastSmoke.verdict === "PASS");
    let health;
    if (smokeFail) {
      reasons.push("smoke FAIL");
      health = "CRITICAL";
    } else {
      if (crashloop) reasons.push("CrashLoopBackOff");
      if (sanityFail) reasons.push("sanity FAIL");
      if (highRca) reasons.push("HIGH RCA");
      if (restarts) reasons.push("restarts");
      if (notReady) reasons.push("service not ready");
      if (authOpen) reasons.push("AUTH-OPEN");
      const healthyOk =
        allRunning && smokePassed && !crashloop && !highRca && !restarts && !sanityFail && !authOpen;
      if (healthyOk) {
        health = "HEALTHY";
        reasons.push("services Running, smoke PASS, no HIGH RCA");
      } else {
        health = "DEGRADED";
      }
    }
    return {
      health,
      reasons,
      lastSmoke,
      lastSanity,
      crashloop,
      smokeFail,
      sanityFail,
      highRca,
      authOpen,
      allRunning,
      smokePassed,
      fired,
    };
  }

  function healthStatus(data) {
    const bundle = data.fixtures.services;
    const rows = bundle.services;
    const unhealthy = rows.filter((s) => s.status !== "Running" || !s.ready);
    const smoke = runSuite(data, "smoke", null);
    const sanity = runSuite(data, "sanity", null);
    const snapshot = computeAppHealth(data, { lastSmoke: smoke, lastSanity: sanity });
    const health = snapshot.health;
    const perf = data.fixtures.performance;
    const lines = [
      "Quality of GaussIQ 1.0 (demo): " +
        health +
        " on tenant `" +
        bundle.tenant +
        "` queue `" +
        bundle.queue +
        "` (simulated, not live production).",
      "Services: " +
        unhealthy.length +
        " / " +
        rows.length +
        " not ready (" +
        (unhealthy.map((s) => s.id).join(", ") || "none") +
        ").",
      "Open support cases: " +
        data.fixtures.cases.open +
        ". Gross MTTR: " +
        perf.gross_mttr_hours +
        " h. Eng assist: " +
        perf.eng_assist_hours +
        " h.",
      "Root cause (from fixtures):",
    ];
    snapshot.fired.forEach((f) =>
      lines.push("- " + f.severity + " " + f.id + " " + f.component + ": " + f.title)
    );
    const secFired = ((data.security_report || {}).fired) || [];
    if (secFired.length) {
      lines.push("Security (from fixtures):");
      secFired.forEach((f) =>
        lines.push("- " + f.severity + " " + f.id + " " + f.component + ": " + f.title)
      );
    }
    lines.push(
      "Auto-ran smoke: " +
        smoke.verdict +
        " " +
        smoke.passed +
        "/" +
        smoke.total +
        " and sanity: " +
        sanity.verdict +
        " " +
        sanity.passed +
        "/" +
        sanity.total +
        "."
    );
    if (sanity.rcas && sanity.rcas[0]) {
      const rca = sanity.rcas[0];
      lines.push("");
      lines.push(
        "RCA — " +
          (rca.name || rca.id) +
          "\nSymptom: " +
          (rca.symptom || "") +
          "\nCause: " +
          (rca.cause || "") +
          "\nFix: " +
          (rca.fix || "")
      );
    }
    lines.push("");
    lines.push("Full regression is heavier (API + security + performance). Say yes to run it, or no to stop here.");
    return {
      route: "app_status",
      source: "handler:app_status",
      tools: ["run_suite:smoke", "run_suite:sanity", "read_fixture:gaussiq/fixtures/services.json"],
      answer: lines.join("\n"),
      metrics: {
        health,
        health_reasons: snapshot.reasons,
        unhealthy: unhealthy.length,
        open_cases: data.fixtures.cases.open,
        gross_mttr_hours: perf.gross_mttr_hours,
        eng_assist_hours: perf.eng_assist_hours,
        smoke_verdict: smoke.verdict,
        sanity_verdict: sanity.verdict,
      },
      ui: "verdict",
      awaiting_regression: true,
      session_update: { awaiting_regression: true },
      health: { smoke_report: smoke, sanity_report: sanity, health, reasons: snapshot.reasons },
      caveat: caveat(),
    };
  }

  function skipRegression(data) {
    const snapshot = computeAppHealth(data, {
      lastSmoke: runSuite(data, "smoke", null),
      lastSanity: runSuite(data, "sanity", null),
    });
    return {
      route: "skip_regression",
      source: "handler:app_status",
      tools: [],
      answer:
        "Regression skipped. Current quality verdict stays at the smoke + sanity read: GaussIQ 1.0 demo services are " +
        snapshot.health +
        " until signal-connector is Running and AJ18991 is off the cert SAN mismatch.",
      metrics: { regression: "skipped", health: snapshot.health, health_reasons: snapshot.reasons },
      ui: "verdict",
      awaiting_regression: false,
      session_update: { awaiting_regression: false },
      caveat: caveat(),
    };
  }

  function caseRca(data, question) {
    const items = data.fixtures.cases.items;
    const blob = String(question || "").toUpperCase();
    let wanted = items.find((c) => blob.indexOf(c.id) !== -1);
    if (!wanted) wanted = items.find((c) => c.id === "AJ18991") || items[0];
    const report = data.rca_report;
    const lines = [
      "Case " + wanted.id + " — " + wanted.org + " / " + wanted.customer + " / " + wanted.product + ".",
      "Severity " + wanted.severity + ". Region " + wanted.region + ". Status " + wanted.status + ".",
      "Symptom: " + wanted.symptom,
      "Component: " + wanted.component,
      "Likely cause (fixture): " + wanted.likely_cause,
      "Similar DEMO tickets: " + ((wanted.similar || []).join(", ") || "none") + ".",
      "Discarded knowledge: " + ((wanted.kb_discarded || []).join("; ") || "none") + ".",
      "Verify: " + wanted.verification,
      "",
      formatEngineReport(report),
    ];
    return {
      route: "case_rca",
      source: "handler:case_rca",
      tools: ["read_fixture:gaussiq/fixtures/cases.json", "rule_rca:gaussiq/rca_engine.py"],
      answer: lines.join("\n"),
      metrics: {
        case_id: wanted.id,
        open_cases: data.fixtures.cases.open,
        fired: (report.fired || []).map((r) => r.id),
        skipped: (report.skipped || []).map((r) => r.id),
      },
      ui: "rca",
      rca: report,
      case: wanted,
      caveat: caveat(),
    };
  }

  function whyMttr(data) {
    const p = data.fixtures.performance;
    const b = p.baseline;
    const report = data.rca_report;
    const delta = Math.round((p.gross_mttr_hours - b.gross_mttr_hours) * 10) / 10;
    const direction = delta > 0 ? "above" : "below";
    const lines = [
      "Gross MTTR is " +
        p.gross_mttr_hours +
        " hours in this demo fixture, " +
        Math.abs(delta) +
        " hours " +
        direction +
        " the lab baseline of " +
        b.gross_mttr_hours +
        ".",
      "Net MTTR " +
        p.net_mttr_hours +
        " h vs baseline " +
        b.net_mttr_hours +
        ". Eng assist " +
        p.eng_assist_hours +
        " h vs " +
        b.eng_assist_hours +
        ".",
      "These are original demo-tenant fixtures, not live production and not GaussIQ published ranges.",
      "Why it is high in this snapshot:",
    ];
    (report.fired || []).forEach((row) => {
      if (["CERT-MISMATCH", "CONNECTOR-LAG", "SKILL-GAP-TLS"].indexOf(row.id) !== -1) {
        lines.push("- " + row.id + ": " + row.title);
      }
    });
    lines.push("");
    lines.push("Checked — not the cause: APP-CODE-500 (the 500 is the cert), CPU-HOT, INSIGHTS-DOWN.");
    lines.push("");
    lines.push(formatEngineReport(report));
    return {
      route: "why_mttr",
      source: "handler:why_mttr",
      tools: ["read_fixture:gaussiq/fixtures/performance.json", "rule_rca:gaussiq/rca_engine.py"],
      answer: lines.join("\n"),
      metrics: {
        gross_mttr_hours: p.gross_mttr_hours,
        baseline_gross_mttr_hours: b.gross_mttr_hours,
        delta_hours: delta,
        fired: (report.fired || []).map((r) => r.id),
      },
      ui: "rca",
      rca: report,
      caveat: caveat(),
    };
  }

  function perfMetrics(data) {
    const p = data.fixtures.performance;
    const b = p.baseline;
    const lines = [
      "Performance fixture for tenant `" + p.tenant + "` (" + p.window + "). Snapshot `" + p.generated_at + "`.",
      p.note,
      "Gross MTTR: " + p.gross_mttr_hours + " hours (baseline " + b.gross_mttr_hours + ").",
      "Net MTTR: " + p.net_mttr_hours + " hours (baseline " + b.net_mttr_hours + ").",
      "Eng assist: " + p.eng_assist_hours + " hours (baseline " + b.eng_assist_hours + ").",
      "Open cases: " + p.open_cases + ". Resolved in 7 days: " + p.resolved_7d + ".",
      "Gross MTTR is open-to-close including wait. Net MTTR pauses customer wait. Eng assist is engineer touch time.",
      "These are original demo-tenant numbers, not GaussIQ published 10–20% marketing ranges.",
    ];
    return {
      route: "perf_metrics",
      source: "handler:perf_metrics",
      tools: ["read_fixture:gaussiq/fixtures/performance.json"],
      answer: lines.join("\n"),
      metrics: {
        gross_mttr_hours: p.gross_mttr_hours,
        net_mttr_hours: p.net_mttr_hours,
        eng_assist_hours: p.eng_assist_hours,
        open_cases: p.open_cases,
      },
      ui: "performance",
      caveat: caveat(),
    };
  }

  function skillsGaps(data) {
    const bundle = data.fixtures.skills;
    const lines = [
      "Skills Intelligence fixture for `" + bundle.tenant + "`. " + bundle.note,
      "High-impact gaps: " + bundle.high_impact_gaps + ".",
    ];
    bundle.items.forEach((row) => {
      lines.push(
        "- " +
          row.skill +
          " demand=" +
          row.demand +
          " coverage=" +
          row.coverage +
          " recency_days=" +
          row.recency_days
      );
      lines.push("  " + row.why);
    });
    return {
      route: "skills_gaps",
      source: "handler:skills_gaps",
      tools: ["read_fixture:gaussiq/fixtures/skills.json"],
      answer: lines.join("\n"),
      metrics: { high_impact_gaps: bundle.high_impact_gaps, skills: bundle.items.map((r) => r.skill) },
      ui: "skills",
      caveat: caveat(),
    };
  }

  function serviceHealth(data) {
    const bundle = data.fixtures.services;
    const rows = bundle.services;
    const unhealthy = rows.filter((s) => s.status !== "Running" || !s.ready);
    const lines = [
      "24x7 health of GaussIQ 1.0 demo services on `" + bundle.tenant + "` (" + bundle.note + ").",
      unhealthy.length + " of " + rows.length + " services are not ready:",
    ];
    rows.forEach((s) => {
      lines.push(
        "- `" +
          s.id +
          "` (" +
          s.product +
          "): status=" +
          s.status +
          " restarts=" +
          s.restarts +
          " CPU " +
          s.cpu_pct +
          "% of limit · memory " +
          s.memory_mib +
          "/" +
          s.memory_limit_mib +
          " MiB. " +
          s.probe
      );
    });
    lines.push("");
    lines.push(formatEngineReport(data.rca_report));
    return {
      route: "service_health",
      source: "handler:service_health",
      tools: ["read_fixture:gaussiq/fixtures/services.json"],
      answer: lines.join("\n"),
      metrics: {
        unhealthy: unhealthy.length,
        service_count: rows.length,
        cpu: rows.reduce((acc, s) => {
          acc[s.id] = s.cpu_pct;
          return acc;
        }, {}),
      },
      ui: "health",
      rca: data.rca_report,
      caveat: caveat(),
    };
  }

  function perfRca(data) {
    const report = data.rca_report;
    return {
      route: "perf_rca",
      source: "handler:perf_rca",
      tools: ["rule_rca:gaussiq/rca_engine.py"],
      answer: formatEngineReport(report),
      metrics: {
        fired: (report.fired || []).map((r) => r.id),
        skipped: (report.skipped || []).map((r) => r.id),
        counts: report.counts || {},
        unhealthy: report.unhealthy,
      },
      ui: "rca",
      rca: report,
      caveat: caveat(),
    };
  }

  function securityRca(data) {
    const report = data.security_report;
    return {
      route: "security_rca",
      source: "handler:security_rca",
      tools: ["rule_rca:gaussiq/security_engine.py", "read_fixture:gaussiq/fixtures/security.json"],
      answer: formatEngineReport(report),
      metrics: {
        fired: (report.fired || []).map((r) => r.id),
        skipped: (report.skipped || []).map((r) => r.id),
        counts: report.counts || {},
      },
      ui: "security",
      security: report,
      caveat: caveat(),
    };
  }

  function loginApi(data, question) {
    const creds = extractCredentials(question);
    const accounts = (((data.fixtures || {}).users || {}).accounts) || [];
    if (!creds.username || !creds.password) {
      return {
        route: "login_api",
        source: "handler:login_api",
        tools: ["read_fixture:gaussiq/fixtures/users.json"],
        answer:
          "This lab will not invent credentials. Say: test the login with username as giquser and password as giqpass (fictional lab user).",
        metrics: { status: 400, ok: false },
        ui: "api_result",
        caveat: caveat(),
      };
    }
    const row = accounts.find((a) => a.username === creds.username);
    if (!row || row.password !== creds.password) {
      return {
        route: "login_api",
        source: "handler:login_api",
        tools: ["read_fixture:gaussiq/fixtures/users.json"],
        answer:
          "POST `/lab/login` username=`" +
          creds.username +
          "` → 401 invalid credentials.\nRCA — login rejected\nSymptom: session was not created.\nEvidence: compared the payload to gaussiq/fixtures/users.json.\nCause: username missing from the lab roster, or password did not match.\nFix: use the documented lab pair giquser / giqpass. Do not retry with invented users.",
        metrics: { ok: false, status: 401, username: creds.username },
        ui: "api_result",
        caveat: caveat(),
      };
    }
    return {
      route: "login_api",
      source: "handler:login_api",
      tools: ["http:POST /lab/login", "read_fixture:gaussiq/fixtures/users.json"],
      answer:
        "POST `/lab/login` → 200 OK.\nActor `" +
        row.displayName +
        "` (" +
        row.role +
        ").\nFictional lab user only. This is not a GaussIQ employee account.",
      metrics: { ok: true, status: 200, username: creds.username },
      ui: "api_result",
      caveat: caveat(),
    };
  }

  function kbRetrieve(data, question) {
    const entries = (((data.fixtures || {}).kb || {}).entries) || [];
    const q = String(question || "").toLowerCase();
    function score(entry) {
      let n = 0;
      (entry.keywords || []).forEach((kw) => {
        if (q.indexOf(kw.toLowerCase()) !== -1) n += 4;
      });
      const hay = [entry.id, entry.title, entry.summary, (entry.keywords || []).join(" ")].join(" ").toLowerCase();
      (q.match(/[a-z0-9]+/g) || []).forEach((token) => {
        if (hay.indexOf(token) !== -1) n += 1;
      });
      return n;
    }
    const ranked = entries.map((e) => [score(e), e]).sort((a, b) => b[0] - a[0]);
    if (!ranked.length || ranked[0][0] <= 0) {
      return {
        route: "kb_retrieve",
        source: "kb:none",
        tools: ["kb_search:gaussiq/fixtures/kb.json"],
        answer: "The catalog has no matching public-concept entry. No number was generated.",
        metrics: null,
        ui: null,
        caveat: caveat(),
      };
    }
    const best = ranked[0][1];
    return {
      route: "kb_retrieve",
      source: "kb:" + best.id,
      tools: ["kb_search:gaussiq/fixtures/kb.json", "read_doc:" + best.citation],
      answer: best.title + ".\n" + best.summary + "\nCitation: `" + best.citation + "`.",
      metrics: null,
      citations: [best.citation],
      match: { id: best.id, score: ranked[0][0] },
      ui: null,
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
      tools: ["read_fixture:gaussiq/fixtures/suites.json"],
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

  function suiteExplain(data, question) {
    const inferred = inferSuite(question);
    const suite = inferred.suite || "sanity";
    const summary = runSuite(data, suite, inferred.layer || null);
    return {
      route: "suite_explain",
      source: "handler:suite_explain",
      tools: ["read_fixture:gaussiq/fixtures/suites.json"],
      answer: formatSuite(summary),
      metrics: {
        suite,
        layer: inferred.layer || null,
        passed: summary.passed,
        failed: summary.failed,
        total: summary.total,
        verdict: summary.verdict,
        mode: "read",
      },
      ui: "suite_explain",
      report: summary,
      caveat: caveat(),
    };
  }

  function fallback() {
    return {
      route: "fallback",
      source: "fallback:deterministic",
      tools: [],
      answer:
        "No handler or catalog entry matched that question. This sample does not call a language model, so it will not invent MTTR, skill counts, or case totals. Try: current state of GaussIQ 1.0 demo services, why AJ18991 returned HTTP 500, gross MTTR, skill gaps, any security issues, login with giquser/giqpass, run smoke, run sanity, or run regression.",
      metrics: null,
      ui: null,
      caveat: caveat(),
    };
  }

  const YES = /^\s*(y|yes|yeah|yep|ok|okay|sure|do it|go ahead|please run|run it|run them|run regression)\b/i;
  const NO = /^\s*(n|no|nope|skip|not now|later|don't|dont)\b/i;

  const HANDLERS = {
    login_api: loginApi,
    suite_explain: suiteExplain,
    run_suite: runNamedSuite,
    app_status: healthStatus,
    case_rca: caseRca,
    skills_gaps: skillsGaps,
    why_mttr: whyMttr,
    perf_metrics: perfMetrics,
    security_rca: securityRca,
    perf_rca: perfRca,
    service_health: serviceHealth,
    kb_retrieve: kbRetrieve,
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
        return annotateSource(Object.assign(skipRegression(data), { question: text, model_available: false }));
      }
    }
    if (!text) {
      const empty = fallback();
      empty.question = "";
      empty.model_available = false;
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

  function renderSuiteCard(target, result) {
    const summary = (result && result.report) || {};
    const card = document.createElement("div");
    card.className = "suite-card";
    card.setAttribute("data-testid", "suite-card");
    const h = document.createElement("p");
    h.className = "suite-headline";
    h.setAttribute("data-testid", "suite-headline");
    const body = formatSuite(summary).split("\n");
    h.textContent = body[0] || "suite";
    card.appendChild(h);
    const ul = document.createElement("ul");
    ul.className = "suite-tests";
    const fails = (summary.cases || []).filter((c) => c.status === "fail");
    const rows = fails.length ? fails : summary.cases || [];
    rows.forEach((row) => {
      const li = document.createElement("li");
      li.textContent = row.status === "fail" ? (row.name || row.id) + " — " + plainFailWhy(row) : row.name || row.id;
      ul.appendChild(li);
    });
    card.appendChild(ul);
    const foot = document.createElement("p");
    foot.className = "suite-footnote";
    foot.textContent = "Catalog replay — not a live pytest run.";
    card.appendChild(foot);
    target.appendChild(card);
  }

  root.GiqLabRouter = { route, runSuite, computeAppHealth, renderSuiteCard };
})(window);
