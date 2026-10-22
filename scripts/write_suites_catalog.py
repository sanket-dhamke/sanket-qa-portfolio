#!/usr/bin/env python3
"""Write agent/fixtures/suites.json 1:1 with pytest layer+suite (plus perf extras)."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "agent" / "fixtures" / "suites.json"

MAE_RCA = {
    "symptom": "Search documents go stale while GMS list/count APIs still return 115 datasets.",
    "evidence": [
        "datahub-mae-consumer status=CrashLoopBackOff, restarts=7, last_reason=OOMKilled",
        "memory 1536 / 1536 MiB in the 5m fixture",
        "RCA MEM-PRESSURE fired; PROBE-KILL skipped because last_reason is OOMKilled",
    ],
    "cause": "MAE consumer cannot apply MetadataAuditEvent_v4 after OOM. App health is DEGRADED, not HEALTHY.",
    "fix": "Raise datahub-mae-consumer memory toward 2Gi, confirm Kafka lag on MetadataAuditEvent_v4, then reindex. Do not treat GMS /health passing as an all-clear.",
}

UI_SEARCH_RCA = {
    "symptom": "Dataset search in the UI returns no rows even though GraphQL assetCounts still reports 115 datasets.",
    "evidence": [
        "datahub-mae-consumer status=CrashLoopBackOff, restarts=7, last_reason=OOMKilled",
        "memory 1536 / 1536 MiB in the 5m fixture",
        "open incident inc-1001 Search index lag after MAE consumer OOM",
    ],
    "cause": "MAE consumer cannot apply MetadataAuditEvent_v4, so Elasticsearch search documents are stale. List/count APIs that read GMS still pass; the UI search path does not.",
    "fix": "Raise datahub-mae-consumer memory toward 2Gi, confirm Kafka lag on MetadataAuditEvent_v4, then reindex. Do not treat this as a frontend selector bug.",
}

PERF_RCA = {
    "symptom": "MAE pod has zero memory headroom.",
    "evidence": [
        "metrics fixture cpu 88.1%, memory at limit",
        "RCA finding: OOMKilled then CrashLoopBackOff",
    ],
    "cause": "1536 MiB is too small for MAE + Elasticsearch bulk buffers at even 140 assets.",
    "fix": "This is the first config change before any 1M / 10M ingest plan.",
}


def case(
    cid: str,
    name: str,
    layer: str,
    suite: str,
    *,
    status: str = "pass",
    duration_ms: int = 40,
    endpoint: str | None = None,
    expected: str = "ok",
    actual: str = "ok",
    rca: dict | None = None,
) -> dict:
    return {
        "id": cid,
        "name": name,
        "layer": layer,
        "suites": [suite],
        "endpoint": endpoint,
        "status": status,
        "duration_ms": duration_ms,
        "expected": expected,
        "actual": actual,
        "rca": rca,
    }


CASES = [
    case("api.health", "GMS GET /health", "api", "smoke", duration_ms=42, endpoint="rest.health",
         expected="200 {ok: true, component: datahub-gms}", actual="200 ok=true"),
    case("api.config", "GMS GET /config", "api", "smoke", duration_ms=51, endpoint="rest.config",
         expected="managedIngestion.enabled true", actual="enabled true, defaultCliVersion 0.14.1"),
    case("api.login", "POST /logIn emuser / empass", "api", "smoke", duration_ms=88, endpoint="rest.logIn",
         expected="200 session actor urn:li:corpuser:emuser", actual="200 PLAY_SESSION set, actor emuser"),
    case("api.login_payload", "POST /logIn from login.json payload", "api", "smoke", duration_ms=76, endpoint="rest.logIn",
         expected="200 actor emuser", actual="200 actor emuser"),
    case("api.list_sources", "GraphQL listIngestionSources", "api", "smoke", duration_ms=120, endpoint="graphql.listIngestionSources",
         expected="total 2 (postgres-analytics, oracle-finance)", actual="total 2, assets 86 + 54"),
    case("api.gms_pod", "GMS pod Running matches /health", "api", "smoke", duration_ms=22,
         expected="datahub-gms Running ready=true", actual="Running ready=true"),
    case("api.asset_counts", "GraphQL searchAcrossEntities dataset total", "api", "sanity", duration_ms=134, endpoint="graphql.searchAcrossEntities",
         expected="datasets 115, assets 140", actual="datasets 115"),
    case("api.ingest_create_poll", "Create postgres source then poll execution", "api", "sanity", duration_ms=210, endpoint="graphql.createIngestionSource",
         expected="PENDING then RUNNING then SUCCESS durationMs=18420", actual="SUCCESS 18420"),
    case("api.incidents", "GraphQL listIncidents (alerts)", "api", "sanity", duration_ms=97, endpoint="graphql.listIncidents",
         expected="open incidents 3", actual="open 3, total 5"),
    case("api.ingest_proposal", "REST ingestProposal schemaMetadata", "api", "sanity", duration_ms=188, endpoint="rest.ingestProposal",
         expected="success true", actual="success true"),
    case(
        "api.mae_search_index",
        "MAE consumer ready so search index stays current",
        "api",
        "sanity",
        status="fail",
        duration_ms=28,
        expected="datahub-mae-consumer Running, ready=true, last_reason empty",
        actual="CrashLoopBackOff restarts=7 last_reason=OOMKilled exit=137",
        rca=MAE_RCA,
    ),
    case("api.search_across_entities", "searchAcrossEntities total is 115", "api", "sanity", duration_ms=110, endpoint="graphql.searchAcrossEntities",
         expected="total 115", actual="total 115"),
    case("api.incident_mae_lag", "Open incidents include MAE search lag", "api", "sanity", duration_ms=90, endpoint="graphql.listIncidents",
         expected="inc-1001 Search index lag after MAE consumer OOM", actual="open 3 includes MAE lag"),
    case("api.postgres_source", "postgres-analytics still listed", "api", "sanity", duration_ms=80, endpoint="graphql.listIngestionSources",
         expected="postgres-analytics type=postgres assets=86", actual="86"),
    case("api.config_cli_version", "managedIngestion CLI 0.14.1", "api", "sanity", duration_ms=44, endpoint="rest.config",
         expected="defaultCliVersion 0.14.1", actual="0.14.1"),
    case("api.frontend_pod", "datahub-frontend Running", "api", "sanity", duration_ms=18,
         expected="Running ready=true restarts=0", actual="Running"),
    case("api.mce_recovered", "datahub-mce-consumer recovered", "api", "sanity", duration_ms=19,
         expected="Running after 2 Error restarts", actual="Running ready=true last_reason=Error"),
    case("api.health_while_mae_down", "GMS /health ok while MAE is down", "api", "sanity", duration_ms=55, endpoint="rest.health",
         expected="ok true and mae CrashLoopBackOff", actual="ok true; mae OOMKilled"),
    case("api.login_bad_password", "Login rejects bad password", "api", "regression", duration_ms=40, endpoint="rest.logIn",
         expected="401", actual="401"),
    case("api.login_missing_body", "Login missing body unauthorized", "api", "regression", duration_ms=36, endpoint="rest.logIn",
         expected="401", actual="401"),
    case("api.graphql_unknown", "Unknown GraphQL operation returns errors", "api", "regression", duration_ms=33, endpoint="graphql",
         expected="400 errors mock GMS", actual="400 errors"),
    case("api.unsupported_aspect", "Unsupported aspect action fails", "api", "regression", duration_ms=31, endpoint="rest.ingestProposal",
         expected="success false", actual="success false"),
    case("api.reset_source", "Reset clears created ingestion source", "api", "regression", duration_ms=70,
         expected="list sources back to 2", actual="total 2"),
    case("api.login_unknown_user", "Unknown user unauthorized", "api", "regression", duration_ms=38, endpoint="rest.logIn",
         expected="401", actual="401"),
    case("api.dataset_unknown", "dataset GraphQL not implemented", "api", "regression", duration_ms=29, endpoint="graphql.dataset",
         expected="400 errors", actual="400 errors"),
    case("api.health_lab_mock", "Health mode is lab-mock", "api", "regression", duration_ms=24, endpoint="rest.health",
         expected="mode lab-mock", actual="lab-mock"),
    case("api.sources_assets_sum", "Listed source assets sum to 140", "api", "regression", duration_ms=95, endpoint="graphql.listIngestionSources",
         expected="86+54=140", actual="140"),
    case("api.ingest_proposal_urn", "ingestProposal default orders urn", "api", "regression", duration_ms=48, endpoint="rest.ingestProposal",
         expected="analytics.public.orders", actual="orders urn"),
    case("api.create_source_inline", "Inline createIngestionSource mutation", "api", "regression", duration_ms=62, endpoint="graphql.createIngestionSource",
         expected="urn:li:dataHubIngestionSource:*", actual="urn minted"),
    case("api.exec_pending_running", "Execution poll PENDING then RUNNING", "api", "regression", duration_ms=84, endpoint="graphql.listExecutionRequests",
         expected="PENDING then RUNNING", actual="PENDING, RUNNING"),
    case("api.mae_memory_limit", "MAE memory is at the pod limit", "api", "regression", duration_ms=16,
         expected="1536 / 1536 MiB", actual="1536 / 1536"),
    case("api.gms_heap_opts", "GMS java opts set heap", "api", "regression", duration_ms=15,
         expected="-Xms1g -Xmx2g", actual="-Xms1g -Xmx2g"),
    case("api.actions_pod", "datahub-actions executor Running", "api", "regression", duration_ms=17,
         expected="Running ready=true 2048 MiB", actual="Running"),
    case("api.oracle_source", "oracle-finance source present", "api", "regression", duration_ms=78, endpoint="graphql.listIngestionSources",
         expected="oracle assets 54", actual="54"),
    case("api.config_stateful", "config statefulIngestionCapable", "api", "regression", duration_ms=27, endpoint="rest.config",
         expected="true", actual="true"),
    case("api.duplicate_source_urns", "Duplicate creates get unique urns", "api", "regression", duration_ms=66, endpoint="graphql.createIngestionSource",
         expected="two distinct urns", actual="urns differ"),
    case("ui.home_cards", "Home shows name and three cards", "ui", "smoke", duration_ms=640,
         expected="heading Sanket Dhamke; Hybrid Agent, API Automation, UI Automation", actual="visible"),
    case("ui.console_connect_hidden", "Console starts on Connect, monitoring hidden", "ui", "smoke", duration_ms=520,
         expected="connect-gate visible, monitor hidden", actual="visible"),
    case("ui.console_refresh_connect", "Connect then refresh returns to Connect", "ui", "smoke", duration_ms=710,
         expected="connect-gate after reload", actual="visible"),
    case("ui.email_preview", "Email preview default To sanket", "ui", "sanity", duration_ms=980,
         expected="sanket.dhamke@gmail.com, SMTP=none", actual="preview sent"),
    case("ui.console_oom_chip", "Canned OOM question shows handler chip", "ui", "sanity", duration_ms=640,
         expected="handler:pod_status", actual="handler:pod_status"),
    case("ui.graphql_kb_chip", "GraphQL mutation chip is knowledge base", "ui", "sanity", duration_ms=610,
         expected="kb:graphql.createIngestionSource", actual="kb"),
    case("ui.enter_clears", "Enter clears the question box", "ui", "sanity", duration_ms=430,
         expected="composer empty after ask", actual="empty"),
    case("ui.login_chip", "Login chip shows emuser", "ui", "sanity", duration_ms=690,
         expected="urn:li:corpuser:emuser", actual="emuser"),
    case("ui.api_page", "API page is API-only", "ui", "sanity", duration_ms=540,
         expected="tests/api/smoke, no Playwright", actual="visible"),
    case("ui.ui_page", "UI page shows UI tree not API payloads", "ui", "sanity", duration_ms=530,
         expected="pages/ and tests/ui/", actual="visible"),
    case("ui.architecture", "Architecture states model does not choose tools", "ui", "sanity", duration_ms=500,
         expected="Does not choose tools", actual="visible"),
    case("ui.app_health_rca", "Console App health DEGRADED and Performance RCA", "ui", "sanity", duration_ms=860,
         expected="DEGRADED, MEM-PRESSURE, table above RCA", actual="DEGRADED"),
    case(
        "ui.search_datasets",
        "UI search returns postgres datasets",
        "ui",
        "sanity",
        status="fail",
        duration_ms=1840,
        endpoint="graphql.searchAcrossEntities",
        expected="results include analytics.public.orders",
        actual="empty result list; index lag banner",
        rca=UI_SEARCH_RCA,
    ),
    case("ui.tools_tab", "Tools tab and CPU % of pod limit", "ui", "regression", duration_ms=720,
         expected="handler:tool_catalog, gms_heap", actual="visible"),
    case("ui.postgres_ingest", "Postgres ingest opens recipe and run id", "ui", "regression", duration_ms=1100,
         expected="createIngestionSource run id", actual="run id minted"),
    case("ui.perf_table_above_rca", "Performance pod table is above RCA", "ui", "regression", duration_ms=780,
         expected="pod-table y < perf-rca y", actual="table first"),
    case("ui.perf_no_http_000", "Performance never shows HTTP 000", "ui", "regression", duration_ms=790,
         expected="plain mae/mce health-check lines", actual="plain language"),
    case("ui.perf_checked_not_cause", "Checked — not the cause on Performance", "ui", "regression", duration_ms=770,
         expected="PROBE-KILL ruled out", actual="Checked — not the cause"),
    case("ui.rca_tab_plain", "RCA tab plain language", "ui", "regression", duration_ms=740,
         expected="no HTTP 000, no not fired", actual="plain"),
    case("ui.capacity_tab", "Capacity tab 140-asset fixture", "ui", "regression", duration_ms=700,
         expected="140-asset fixture", actual="visible"),
    case("ui.email_subject_degraded", "Email subject is DEGRADED", "ui", "regression", duration_ms=920,
         expected="DEGRADED, no HTTP 000", actual="DEGRADED"),
    case("ui.suites_tab_sanity", "Suites tab after API sanity", "ui", "regression", duration_ms=880,
         expected="sanity FAIL", actual="FAIL"),
    case("ui.health_kpi", "App health KPI is DEGRADED not unknown", "ui", "regression", duration_ms=650,
         expected="DEGRADED", actual="DEGRADED"),
    case("ui.suite_strip_ui", "UI framework suite strip pyramid", "ui", "regression", duration_ms=560,
         expected="smoke < sanity < regression", actual="pyramid"),
    case("ui.suite_strip_api", "API framework suite strip pyramid", "ui", "regression", duration_ms=550,
         expected="smoke < sanity < regression", actual="pyramid"),
    case("ui.about_page", "About page is not a live cluster", "ui", "regression", duration_ms=480,
         expected="Not a hosted DataHub cloud", actual="visible"),
    case("ui.home_nav_console", "Home nav opens lab console", "ui", "regression", duration_ms=610,
         expected="console.html connect-gate", actual="visible"),
    case("ui.architecture_footer", "Architecture footer says simulated", "ui", "regression", duration_ms=470,
         expected="simulated", actual="visible"),
    case("ui.allure_link", "UI Allure link is separate from API", "ui", "regression", duration_ms=490,
         expected="reports/allure-ui/index.html", actual="href allure-ui"),
    case(
        "perf.mae_memory_headroom",
        "MAE consumer memory under 90% of limit",
        "performance",
        "regression",
        status="fail",
        duration_ms=30,
        expected="memory_mib / memory_limit_mib < 0.90",
        actual="1536 / 1536 = 100%",
        rca=PERF_RCA,
    ),
]


def main() -> None:
    counts: dict[str, dict[str, int]] = {}
    for row in CASES:
        layer = row["layer"]
        for suite in row["suites"]:
            counts.setdefault(layer, {})
            counts[layer][suite] = counts[layer].get(suite, 0) + 1
    payload = {
        "generated_at": "2026-10-01T12:00:00Z",
        "note": (
            "Recorded smoke / sanity / regression results for the in-browser agent. "
            "API and UI cases are 1:1 with pytest markers (live excluded). "
            "Performance extras are catalog-only. GitHub Pages cannot spawn pytest, so the handler replays this catalog."
        ),
        "counts": counts,
        "cases": CASES,
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(CASES)} cases) {counts}")


if __name__ == "__main__":
    main()
