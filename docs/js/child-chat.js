/* Scoped child agent on API / UI pages. Same LabRouter as the console. */
(function () {
  const root = document.querySelector("[data-testid=child-chat]");
  if (!root || !window.LabRouter) return;

  const SCOPE = (root.getAttribute("data-layer") || "api").toLowerCase();
  const logEl = root.querySelector("[data-testid=child-log]");
  const jobEl = root.querySelector("[data-testid=child-job]");
  const input = root.querySelector("[data-testid=child-q]");
  const askBtn = root.querySelector("[data-testid=child-ask]");
  const qbank = root.querySelector("[data-testid=qbank]");
  const toggle = root.querySelector("[data-testid=qbank-toggle]");
  const session = {};
  let data = null;

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }

  function withScope(question) {
    let t = String(question || "").trim();
    if (!t) return t;
    const hasLayer = /\b(api|ui)\b/i.test(t);
    const hasSuite = /\b(smoke|sanity|regression)\b/i.test(t);
    if (hasSuite && !hasLayer) {
      t = t.replace(/\b(smoke|sanity|regression)\b/i, SCOPE + " $1");
    }
    return t;
  }

  function inScope(result) {
    const route = (result && result.route) || "";
    if (route === "pipeline_status") return true;
    if (route === "run_suite" || route === "suite_explain") {
      const layer = result.metrics && result.metrics.layer;
      return !layer || layer === SCOPE;
    }
    return false;
  }

  function outOfScopeAnswer() {
    const label = SCOPE === "ui" ? "UI" : "API";
    return (
      "This child agent only answers " +
      label +
      " smoke / sanity / regression. Chat is read; “run …” records a simulated Actions/Jenkins job against the last SHA (no git pull, no Jenkins credentials). The main Hybrid AI Agent on the lab console is the root for performance, security, API, and UI."
    );
  }

  function addMsg(kind, text, result) {
    const el = document.createElement("div");
    el.className = "child-msg " + kind;
    const body = document.createElement("div");
    body.textContent = text;
    el.appendChild(body);
    if (result) {
      const chips = document.createElement("div");
      chips.className = "child-chips";
      const src = document.createElement("span");
      src.dataset.testid = "result-source";
      src.textContent = "source " + (result.source || "");
      chips.appendChild(src);
      const route = document.createElement("span");
      route.textContent = "route " + (result.route || "");
      chips.appendChild(route);
      el.appendChild(chips);
    }
    logEl.appendChild(el);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function paintJob(result) {
    if (!jobEl) return;
    const pipe = (data && data.pipeline) || {};
    const sha = pipe.last_sha_short || (pipe.last_sha || "").slice(0, 7) || "unknown";
    if (result && result.job) {
      const job = result.job;
      jobEl.innerHTML =
        "<strong>Job recorded (write)</strong> " +
        escapeHtml(job.id) +
        " · SHA <code>" +
        escapeHtml(job.sha || sha) +
        "</code> · " +
        escapeHtml(job.provider || "GitHub Actions") +
        " / " +
        escapeHtml(job.jenkins_job || "simulated") +
        " · " +
        escapeHtml(job.verdict || "") +
        " " +
        (job.passed || 0) +
        "/" +
        (job.total || 0) +
        " · git_pull=false · credentials=none";
      return;
    }
    jobEl.innerHTML =
      "<strong>Read only</strong> — no job recorded. Last snapshot SHA <code>" +
      escapeHtml(sha) +
      "</code> on " +
      escapeHtml(pipe.ref || "main") +
      ". Chat does not git-pull. Say “run " +
      SCOPE +
      " smoke” to record a simulated job.";
  }

  function ask(question) {
    const raw = String(question || "").trim();
    if (!raw || !data) return;
    if (input) input.value = "";
    addMsg("user", raw);
    const scoped = withScope(raw);
    const result = window.LabRouter.route(data, scoped, session);
    if (!inScope(result)) {
      const refusal = {
        route: "fallback",
        source: "fallback:child-scope",
        answer: outOfScopeAnswer(),
      };
      addMsg("bot", refusal.answer, refusal);
      paintJob(null);
      return;
    }
    addMsg("bot", result.answer, result);
    paintJob(result);
  }

  function renderBank() {
    if (!qbank || !data) return;
    const bank = ((data.child_questions || {})[SCOPE]) || [];
    qbank.innerHTML = "";
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
        btn.setAttribute("data-testid", "qbank-copy");
        btn.addEventListener("click", () => {
          btn.textContent = "Copied";
          if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(q).catch(function () {});
          }
          setTimeout(() => {
            btn.textContent = "Copy";
          }, 1600);
        });
        row.appendChild(code);
        row.appendChild(btn);
        section.appendChild(row);
      });
      qbank.appendChild(section);
    });
  }

  function bind() {
    if (askBtn) askBtn.addEventListener("click", () => ask(input && input.value));
    if (input) {
      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          ask(input.value);
        }
      });
    }
    if (toggle && qbank) {
      toggle.addEventListener("click", () => {
        const open = qbank.classList.contains("hidden") || qbank.hidden;
        qbank.classList.toggle("hidden", !open);
        qbank.hidden = !open;
        toggle.setAttribute("aria-expanded", open ? "true" : "false");
        if (open) renderBank();
      });
    }
  }

  async function main() {
    const res = await fetch("js/demo-data.json");
    data = await res.json();
    bind();
    paintJob(null);
    addMsg(
      "bot",
      (SCOPE === "ui" ? "UI" : "API") +
        " child agent ready. Same keyword router as the lab console, scoped to this page’s suites. Chat is read; run records a job against last SHA " +
        (((data.pipeline || {}).last_sha_short) || "") +
        ". No git pull. Open “Questions you can ask” to copy a prompt.",
      { source: "handler:pipeline_status", route: "hello" }
    );
  }

  window.LabChildChat = { ask, withScope };
  main();
})();
