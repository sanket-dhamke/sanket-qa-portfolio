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
      " smoke / sanity / regression. Open the main Hybrid AI Agent on the lab console for performance, security, API, and UI."
    );
  }

  function addMsg(kind, text, result) {
    const el = document.createElement("div");
    el.className = "child-msg " + kind;
    const isSuite =
      result &&
      result.report &&
      (result.route === "run_suite" || result.route === "suite_explain" || result.ui === "suite_report");
    if (kind === "bot" && isSuite && window.LabRouter.renderSuiteCard) {
      window.LabRouter.renderSuiteCard(el, result);
    } else {
      const body = document.createElement("div");
      body.textContent = text;
      el.appendChild(body);
    }
    logEl.appendChild(el);
    logEl.scrollTop = logEl.scrollHeight;
  }

  function paintJob(result) {
    if (!jobEl) return;
    const links = (result && result.allure) || [];
    if (result && result.report && links.length) {
      jobEl.innerHTML = "";
      links.forEach((a) => {
        const link = document.createElement("a");
        link.className = "allure-open";
        link.setAttribute("data-testid", "allure-link");
        link.href = a.href;
        link.textContent = a.label;
        jobEl.appendChild(link);
      });
      return;
    }
    if (result && result.report) {
      jobEl.textContent = ((result.answer || "").split("\n")[0]) || "Suite result";
      return;
    }
    jobEl.textContent = "No suite run this session.";
  }

  function ask(question) {
    const raw = String(question || "").trim();
    if (!raw || !data) return;
    if (input) input.value = "";
    addMsg("user", raw);
    const scoped = withScope(raw);
    const result = window.LabRouter.route(data, scoped, session);
    if (!inScope(result)) {
      addMsg("bot", outOfScopeAnswer());
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
        " agent ready. Ask about smoke, sanity, or regression — or open “Questions you can ask” and copy a prompt."
    );
  }

  window.LabChildChat = { ask, withScope };
  main();
})();
