"""GaussIQ lab page is Pages-safe and does not clone forbidden brands."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = ("BMC", "Beacon", "GATEZO", "H2O", "Bedrock", "ODIN")


def _html() -> str:
    return (ROOT / "docs" / "gaussiq.html").read_text(encoding="utf-8")


def test_gaussiq_page_disclaimer_and_no_github_repo() -> None:
    text = _html()
    assert "Not affiliated with GaussIQ" in text
    assert "Not their product" in text
    assert "This is not GaussIQ’s product" in text or "This is not GaussIQ's product" in text
    assert "not employment" in text.lower() or "Not employment" in text
    assert "not live production" in text.lower()
    assert "Quality monitoring for GaussIQ Execution Intelligence" in text
    assert "github.com/sanket-dhamke" not in text
    assert "GitHub repo" not in text
    assert 'id="connect-gate"' in text
    assert 'id="quality-dash"' in text
    assert 'id="chat-panel"' in text
    assert text.find('id="chat-panel"') < text.find('id="kpis"')
    assert text.find('id="chat-panel"') < text.find('id="quality-dash"')
    assert text.find('id="canned"') < text.find('id="q"')
    assert "Ask the quality agent" in text
    assert 'id="ask"' in text
    assert "<textarea" in text
    assert "Type a question" in text
    assert "Platform performance" in text
    assert "Ops KPIs" in text
    assert "cpu-chart" in text
    assert "mem-chart" in text
    assert 'data-testid="qbank-toggle"' in text
    assert "Questions you can ask" in text
    css = (ROOT / "docs" / "css" / "gaussiq.css").read_text(encoding="utf-8")
    assert ".composer #ask" in css or "button#ask" in css
    assert "box-shadow" in css
    assert "5.5rem" in css
    assert "#f4ead8" in css
    assert "rocket-pack-lab" in text
    assert "Try this out" in text
    assert "Why is MTTR high" in (ROOT / "gaussiq" / "router.py").read_text(encoding="utf-8")
    assert "bedrock" not in text.lower()
    js = (ROOT / "docs" / "js" / "gaussiq-lab.js").read_text(encoding="utf-8").lower()
    assert "bedrock" not in js
    assert "amazonaws.com" not in js


def test_gaussiq_tree_has_no_forbidden_brands() -> None:
    paths = list((ROOT / "gaussiq").rglob("*"))
    paths += [
        ROOT / "docs" / "gaussiq.html",
        ROOT / "docs" / "css" / "gaussiq.css",
        ROOT / "docs" / "js" / "gaussiq-router.js",
        ROOT / "docs" / "js" / "gaussiq-lab.js",
        ROOT / "docs" / "js" / "gaussiq-data.json",
        ROOT / "docs" / "index.html",
    ]
    for path in paths:
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".py", ".json", ".html", ".js", ".css", ".md"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for word in FORBIDDEN:
            assert word not in text, f"{word} in {path}"
        assert "github.com/sanket-dhamke" not in text or path.name == "README.md"


def test_about_says_not_gaussiq_product() -> None:
    text = (ROOT / "docs" / "about.html").read_text(encoding="utf-8")
    assert "not GaussIQ" in text
    assert "Not employment" in text or "not employment" in text.lower()
    assert "not live production" in text.lower()
    assert 'href="gaussiq.html"' in text
    assert "github.com/sanket-dhamke" not in text


def test_home_has_gaussiq_card_and_keeps_datahub_hero() -> None:
    text = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert "Open the Hybrid AI Agent for performance testing" in text
    assert 'href="console.html"' in text
    assert "GaussIQ QA lab (demo)" in text
    cards = text.split('class="cards"', 1)[1]
    gq = cards.split("GaussIQ QA lab (demo)", 1)[1].split("</article>", 1)[0]
    assert 'href="gaussiq.html"' in gq
    assert "Try this out" in gq
    assert 'data-testid="try-this-gaussiq"' in gq
    hero = text.split('class="hero"', 1)[1].split("</section>", 1)[0]
    assert "GaussIQ QA lab (demo)" not in hero
    assert "DataHub lab" in hero or "this DataHub lab" in hero
