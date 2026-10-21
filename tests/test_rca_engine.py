"""Rule RCA: OOM vs probe, skipped rules, DataHub-only copy."""

from __future__ import annotations

import re
from pathlib import Path

from agent.rca_engine import evaluate, format_report
from agent.router import route

ROOT = Path(__file__).resolve().parents[1]


def test_mae_oom_fires_memory_not_probe() -> None:
    report = evaluate()
    fired = {row["id"]: row for row in report["fired"]}
    skipped = {row["id"]: row["why"] for row in report["skipped"]}
    assert "MEM-PRESSURE" in fired
    evidence = " ".join(fired["MEM-PRESSURE"].get("evidence") or [])
    assert "OOMKilled" in evidence or "OOMKilled" in fired["MEM-PRESSURE"]["observation"]
    assert "PROBE-KILL" in skipped
    assert "OOMKilled" in skipped["PROBE-KILL"]
    assert "INDEXING" in fired
    assert "GMS-HEAP" in skipped
    assert "SIZING" in skipped
    assert report["unhealthy"] >= 1


def test_why_slow_uses_handler_and_skipped_rules() -> None:
    result = route("Why is DataHub slow?")
    assert result["source"] == "handler:perf_rca"
    assert result["source_kind"] == "handler"
    assert "MEM-PRESSURE" in result["metrics"]["fired"]
    assert "PROBE-KILL" in result["metrics"]["skipped"]
    assert "Evaluated, not fired" in result["answer"]
    assert result["metrics"] is not None


def test_source_kinds_split_handler_kb_suite() -> None:
    pods = route("Which pods are crashing or restarting after OOM?")
    kb = route("What GraphQL mutation creates an ingestion source?")
    suite = route("Check UI sanity")
    miss = route("write me a poem about lunch")
    assert pods["source_kind"] == "handler"
    assert kb["source_kind"] == "kb"
    assert kb["source"].startswith("kb:")
    assert suite["source_kind"] == "suite"
    assert miss["source_kind"] == "fallback"


def test_home_copy_is_agentic_and_has_no_city() -> None:
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Lead SDET in Pune" not in text
    assert "Pune" not in text
    assert "AI-based, agentic QA" in text
    assert "never from a model guessing" in text
    assert "RLHF" not in text
    assert "This site is an original public sample" not in text
    main = text.split("<main", 1)[1].split("</main>", 1)[0]
    assert "not affiliated with any prior employer" not in main.lower()
    footer = text.split("<footer", 1)[1]
    assert "Not affiliated" in footer
    assert "simulated" in footer
    for name in (
        "architecture.html",
        "about.html",
        "api-framework.html",
        "ui-framework.html",
        "index.html",
    ):
        page = (ROOT / "docs" / name).read_text(encoding="utf-8")
        assert "Pune" not in page
        stripped = re.sub(r"<header[\s\S]*?</header>", "", page, count=1)
        body = stripped.split("<body", 1)[-1]
        assert not re.search(r">\s*This site is", body)


def test_architecture_states_ai_boundary() -> None:
    text = (ROOT / "docs" / "architecture.html").read_text(encoding="utf-8")
    assert "does not decide which tool" in text.lower() or "Does not choose tools" in text
    assert "Does not collect metrics" in text
    assert "Does not set RCA" in text
    cpu = (ROOT / "docs" / "console.html").read_text(encoding="utf-8")
    assert "CPU % of pod limit (not node)" in cpu
    assert 'data-tab="tools"' in cpu


def test_public_tree_has_no_forbidden_product_names() -> None:
    # Scan shipped lab files only — not this test's own pattern string.
    pattern = re.compile(r"\b(beacon|bmc|odin|kubectl|eks|gatezo)\b", re.I)
    roots = [
        ROOT / "agent",
        ROOT / "docs",
        ROOT / "api",
        ROOT / "config",
        ROOT / "utils",
        ROOT / "ui",
        ROOT / "tests" / "api",
        ROOT / "tests" / "helpers",
        ROOT / "tests" / "payloads",
        ROOT / ".cursor",
        ROOT / "README.md",
    ]
    hits: list[str] = []
    files: list[Path] = []
    for root in roots:
        if root.is_file():
            files.append(root)
        elif root.is_dir():
            files.extend(root.rglob("*"))
    for path in files:
        if not path.is_file() or path.suffix.lower() not in {
            ".py",
            ".js",
            ".json",
            ".html",
            ".css",
            ".md",
            ".yml",
            ".yaml",
        }:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if "__pycache__" in rel:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if pattern.search(text):
            hits.append(rel)
    assert hits == [], hits
    assert "kubectl" not in format_report(evaluate()).lower()
