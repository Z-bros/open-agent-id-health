"""E06 TB-CareOS local human-review dashboard for fabricated administrative evidence.

Renders inert self-contained HTML. No JavaScript, network calls, patient outreach,
approvals, or updates to source systems. Trust boundaries are checked before render.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
import re

from apps.caselens.explain import CaseLensValidationError, _context
from apps.nextstep.plan import NextStepValidationError, _check_explanation, validate_plan

STYLE = """
:root{color-scheme:light;--ink:#1b2940;--muted:#627087;--blue:#315cc9;
--surface:#f6f8fc;--line:#dce3ef;--white:#fff;--cyan:#e9f3fd;
--red:#9e3636;--green:#235e48;--gold:#815516}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;background:var(--surface);color:var(--ink);
font:15px/1.56 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
a{color:var(--blue)}a:focus-visible{outline:3px solid #648aed;outline-offset:3px}
.container{max-width:1160px;margin:0 auto;padding:0 26px}
header{background:#14233b;color:#fff;padding:28px 0 30px}
header .eyebrow{letter-spacing:.14em;font-size:11px;text-transform:uppercase;color:#a9caec;font-weight:750}
header h1{font-size:34px;letter-spacing:-.04em;margin:6px 0 5px;line-height:1.2}
header p{margin:0;color:#d3deee}
.headgrid{display:flex;justify-content:space-between;align-items:flex-end;gap:22px;flex-wrap:wrap}
.brand{display:inline-flex;gap:9px;align-items:center;font-weight:750;font-size:13px}
.brandmark{display:inline-flex;width:30px;height:30px;background:#7cd7ba;
color:#11223e;border-radius:9px;align-items:center;justify-content:center;font-size:17px}
.topnav{background:#fff;border-bottom:1px solid var(--line);position:sticky;top:0;z-index:2}
.navwrap{display:flex;gap:22px;overflow-x:auto;padding-top:12px;padding-bottom:12px}
.topnav a{text-decoration:none;color:#394e6b;font-size:13px;font-weight:650;white-space:nowrap}
.topnav a:hover{color:#315cc9}
main{padding:26px 0 70px}
.notice{background:#fff8e8;border:1px solid #efd9a0;border-radius:12px;
padding:14px 18px;font-size:13px;color:#704b16;margin-bottom:22px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin-bottom:25px}
.stat{padding:18px;border:1px solid var(--line);border-radius:14px;background:var(--white)}
.stat b{display:block;font-size:30px;line-height:1.3;letter-spacing:-.04em}
.stat span{font-size:12px;color:var(--muted);font-weight:650}
section{margin:28px 0 0;scroll-margin-top:76px}
.sectionhead{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}
.sectionhead h2{font-size:20px;letter-spacing:-.025em;margin:0}
.sectionhead p{font-size:13px;color:var(--muted);margin:0}
.panel{border:1px solid var(--line);border-radius:14px;background:var(--white);
padding:20px 22px;box-shadow:0 3px 12px rgba(15,31,57,.025)}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.item{border-left:3px solid #8ca5e8;padding:3px 0 3px 16px;margin:12px 0}
.item:first-child{margin-top:0}.item:last-child{margin-bottom:0}
.item h3{font-size:15px;margin:0 0 5px}
.item p{margin:5px 0;color:#34425b}
.small{font-size:12px;color:var(--muted)}
.pill{display:inline-flex;align-items:center;border-radius:999px;font-size:11px;
font-weight:750;padding:4px 10px;background:#edf2fa;color:#3b526f;margin:2px 5px 2px 0}
.pill.ok{background:#e5f6ed;color:var(--green)}
.pill.warn{background:#fff2db;color:var(--gold)}
.pill.err{background:#fff0ec;color:var(--red)}
.pill.info{background:#e7efff;color:#2c58aa}
.pill.code{font-family:ui-monospace,SFMono-Regular,Consolas,monospace;font-size:11px}
.records{width:100%;border-collapse:collapse;text-align:left}
.records th{font-size:11px;text-transform:uppercase;letter-spacing:.06em;color:#667992}
.records th,.records td{padding:12px 10px;border-bottom:1px solid #e8edf4;vertical-align:top}
.records tr:last-child td{border-bottom:0}
.records td{font-size:12px}
code{font:12px ui-monospace,SFMono-Regular,Consolas,monospace;
background:#eff3fa;border-radius:4px;padding:2px 4px;overflow-wrap:anywhere}
.empty{padding:20px;color:var(--muted);background:#fafbfe;border-radius:10px}
.step{display:grid;grid-template-columns:42px minmax(0,1fr);gap:12px;padding:15px 0;
border-bottom:1px solid #e9eef6}
.step:first-child{padding-top:0}.step:last-child{padding-bottom:0;border-bottom:0}
.num{width:32px;height:32px;background:#e6efff;border-radius:9px;display:flex;
align-items:center;justify-content:center;font-weight:750;color:#3159a9}
.step h3{margin:0 0 5px;font-size:15px}
.step p{margin:4px 0 8px;font-size:13px}
.meter{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
.meter .stat b{font-size:24px}
.footer{font-size:12px;color:#627087;margin-top:28px;border-top:1px solid var(--line);padding-top:20px}
@media(max-width:760px){.stats,.meter{grid-template-columns:repeat(2,minmax(0,1fr))}
.grid2{grid-template-columns:1fr}.records th,.records td{padding:9px 5px}
.records{display:block;overflow-x:auto}.container{padding:0 16px}header h1{font-size:27px}}
@media print{.topnav{display:none}header{-webkit-print-color-adjust:exact;print-color-adjust:exact}
section{break-inside:avoid}body{background:white}main{padding-top:10px}}
"""


def _h(value: Any, limit: int = 320) -> str:
    """Render untrusted model/source text only as clipped, escaped text."""
    as_text = str(value if value is not None else "—")
    return escape(as_text[:limit] + ("…" if len(as_text) > limit else ""), quote=True)


def _pill(label: Any, kind: str = "") -> str:
    return '<span class="pill ' + kind + '">' + _h(label, 90) + "</span>"


def _code(value: Any) -> str:
    return "<code>" + _h(value, 90) + "</code>"


def _section(section_id: str, title: str, desc: str, content: str) -> str:
    return (
        '<section id="' + section_id + '"><div class="sectionhead"><h2>' +
        _h(title) + "</h2><p>" + _h(desc) + "</p></div>" +
        '<div class="panel">' + content + "</div></section>"
    )


def _display_time(value: Any) -> str:
    if not isinstance(value, str):
        return "Unknown time"
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt.strftime("%d %b %Y %H:%M UTC")
    except ValueError:
        return "Unverified timestamp"


def _source_check_rows(bundle: dict[str, Any]) -> str:
    latest: dict[str, dict[str, Any]] = {}
    for check in bundle["source_checks"]:
        name = check["source_system"]
        if name not in latest or check["attempt"] > latest[name]["attempt"]:
            latest[name] = check
    from apps.careflow.tb_zetaris_probe import EVIDENCE_SOURCES
    count = Counter(o["record_type"] for o in bundle["observations"])
    cards = []
    for name in EVIDENCE_SOURCES:
        check = latest.get(name)
        status = check["status"] if check else "not_checked"
        color = ("ok" if status == "available" else "warn" if status == "not_found" else "err")
        cards.append(
            '<div class="item"><h3>' + _h(name) + "</h3>" +
            _pill(status, color) + _pill(str(count[name]) + " retrieved rows") +
            ('<p class="small">Attempt ' + _h(check["attempt"]) + '</p>' if check else "") +
            "</div>"
        )
    return '<div class="grid2">' + "".join(cards) + "</div>"


def _findings(bundle: dict[str, Any], explanation: dict[str, Any] | None) -> str:
    issues = bundle["exceptions"]
    if not issues:
        return '<div class="empty">No deterministic administrative discrepancy was identified in this snapshot. This does not establish complete records or completed care.</div>'
    cards = []
    for index, finding in enumerate(issues):
        refs = " ".join(_pill(ref, "code") for ref in finding["evidence_record_ids"])
        explained = None
        if explanation is not None:
            explained = explanation["hypotheses"][index]
        cards.append(
            '<div class="item"><h3>' + _h(finding["category"]) + "</h3>" +
            _pill("CareFlow finding", "warn") +
            (' ' + _pill(explained["assessment"], "info") if explained else "") +
            "<p>" + _h(finding["description"], 700) + "</p>" +
            '<p class="small">Cited evidence</p>' + refs +
            ("<p><strong>CaseLens explanation</strong></p><p>" +
             _h(explained["reason"], 900) + "</p>" if explained else "") +
            "</div>"
        )
    if explanation and explanation["unresolved_questions"]:
        cards.append(
            '<div class="item"><h3>Questions for staff review</h3>' +
            "".join("<p>" + _h(q, 280) + "</p>" for q in explanation["unresolved_questions"][:30]) +
            "</div>"
        )
    elif explanation is None:
        cards.append('<div class="empty">No CaseLens explanation report supplied; findings shown are rule-based only.</div>')
    return "".join(cards)


def _timeline(bundle: dict[str, Any]) -> str:
    entries = sorted(
        bundle["observations"],
        key=lambda item: (str(item.get("observed_at", "")), str(item.get("record_id", ""))),
    )
    rows = []
    for item in entries:
        rows.append(
            "<tr><td>" + _h(_display_time(item.get("observed_at")), 60) +
            "</td><td>" + _h(item["record_type"], 50) +
            "</td><td>" + _code(item["record_id"]) +
            "</td><td>" + _code(item["source_record_id"]) +
            "</td><td>" + _code(item["subject_ref"]) +
            "</td></tr>"
        )
    head = "<thead><tr><th>Observed</th><th>Source table</th><th>Business ID</th><th>Provenance</th><th>Synthetic subject</th></tr></thead>"
    return '<table class="records">' + head + "<tbody>" + "".join(rows) + "</tbody></table>"


def _steps(plan: dict[str, Any] | None) -> str:
    if plan is None:
        return '<div class="empty">No NextStep plan supplied. No action is authorized by this dashboard.</div>'
    output = []
    for i, item in enumerate(plan["actions"], start=1):
        label = {
            "read_only_source_query": "Proposed source check — not executed",
            "manual_review": "Human review required",
            "stop": "Stop: no automatic follow-up",
        }[item["action"]]
        refs = " ".join(_pill(x, "code") for x in item["evidence_record_ids"])
        status = "info" if item["action"] == "read_only_source_query" else "warn"
        output.append(
            '<div class="step"><div class="num">' + str(i) + '</div><div>' +
            "<h3>" + _h(label) + "</h3>" +
            _pill(item["action"], status) +
            (' ' + _pill(item["source_system"]) if "source_system" in item else "") +
            "<p>" + _h(item["reason"], 700) + "</p>" +
            (refs if refs else "") + "</div></div>"
        )
    return "".join(output)


def _meterless(summary: dict[str, Any] | None, case_id: str) -> str:
    if summary is None:
        return '<div class="empty">No Meterless run summary supplied. Audit persistence status is not displayed or inferred.</div>'
    if not isinstance(summary, dict) or summary.get("case_id") != case_id or (
        summary.get("world_model") != "Meterless World Model reference"
    ) or not isinstance(summary.get("durable_state"), dict) or (
        not isinstance(summary.get("replay"), dict)
    ):
        raise ValueError("Meterless summary contract/case mismatch")
    durable = summary["durable_state"]
    values = [
        ("Persisted events", durable.get("event_count")),
        ("Persisted observations", durable.get("observation_count")),
        ("Audit entries", durable.get("audit_count")),
    ]
    if any(type(v) is not int or v < 0 for _, v in values):
        raise ValueError("Meterless summary counters invalid")
    replay = summary["replay"].get("state_unchanged")
    if replay is not True:
        raise ValueError("Meterless sidecar replay not confirmed idempotent")
    return (
        '<div class="meter">' +
        "".join('<div class="stat"><span>' + _h(label) + '</span><b>' +
                str(val) + "</b></div>" for label, val in values) +
        '</div><p class="small">Summary from a separate Meterless World Model run. '
        'It currently covers CareFlow source evidence and findings—not CaseLens '
        'explanations or NextStep plans. Event replay within that run was idempotent; '
        'cold-start derived projections may be rebuilt.</p>'
    )


def render_dashboard(
    bundle: dict[str, Any], *,
    explanation: dict[str, Any] | None = None,
    plan: dict[str, Any] | None = None,
    meterless_summary: dict[str, Any] | None = None,
) -> str:
    """Validate same-case source contracts, then render escaped local HTML."""
    try:
        _context(bundle)
    except CaseLensValidationError as exc:
        raise ValueError("Invalid fabricated evidence bundle: " + str(exc)) from exc
    # Extra structural validation for the source-check timeline used in the UI.
    for check in bundle["source_checks"]:
        if not isinstance(check, dict) or type(check.get("attempt")) is not int or (
            check["attempt"] < 1
        ):
            raise ValueError("Invalid source-check attempt")
    if explanation is not None:
        try:
            _check_explanation(bundle, explanation)
        except NextStepValidationError as exc:
            raise ValueError("Invalid same-case CaseLens report: " + str(exc)) from exc
    if plan is not None:
        try:
            validate_plan(bundle, plan)
        except (NextStepValidationError, CaseLensValidationError) as exc:
            raise ValueError("Invalid same-case NextStep plan: " + str(exc)) from exc

    case_id = bundle["case_id"]
    queries = sum(a["action"] == "read_only_source_query" for a in plan["actions"]) if plan else 0
    stats = [
        (len(bundle["observations"]), "Retrieved observations"),
        (len(bundle["source_checks"]), "Source checks"),
        (len(bundle["exceptions"]), "CareFlow findings"),
        (queries, "Proposed checks only"),
    ]
    stats_html = "".join(
        '<div class="stat"><b>' + str(v) + '</b><span>' + _h(k) +
        "</span></div>" for v, k in stats
    )
    included = [
        ("CareFlow evidence", "ok"),
        ("CaseLens explanation" if explanation else "CaseLens not supplied",
         "ok" if explanation else "warn"),
        ("NextStep plan" if plan else "NextStep not supplied",
         "ok" if plan else "warn"),
    ]
    guide = " ".join(_pill(k, kind) for k, kind in included)
    cards = [
        _section("sources", "Source availability",
                 "Latest status per synthetic Zetaris evidence table", _source_check_rows(bundle)),
        _section("findings", "Administrative findings",
                 "Rule-based exceptions and optional bounded Nemotron explanations",
                 _findings(bundle, explanation)),
        _section("plan", "Proposed verification plan",
                 "Read-only proposals; no follow-up query is executed", _steps(plan)),
        _section("timeline", "Evidence timeline",
                 "Retrieved business IDs, provenance IDs and synthetic subjects",
                 _timeline(bundle)),
        _section("audit", "Meterless audit status",
                 "Separate local persistence summary, when provided",
                 _meterless(meterless_summary, case_id)),
    ]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src &#39;none&#39;; style-src &#39;unsafe-inline&#39;; '
        'img-src &#39;none&#39;; connect-src &#39;none&#39;; '
        'script-src &#39;none&#39;; base-uri &#39;none&#39;; form-action &#39;none&#39;">'
        "<title>TB-CareOS | " + _h(case_id, 60) + "</title>"
        "<style>" + STYLE + "</style></head><body>"
        '<header><div class="container"><div class="headgrid"><div>'
        '<div class="brand"><span class="brandmark">+</span> TB-CareOS / Case review</div>'
        '<div class="eyebrow">Fabricated administrative evidence · Local read-only view</div>'
        "<h1>" + _h(case_id) + "</h1>"
        "<p>Evidence-based review workspace · No real patient records</p>"
        '</div><div>' + _pill("Human review required", "warn") +
        '</div></div></div></header>'
        '<nav class="topnav" aria-label="Dashboard sections"><div class="container navwrap">'
        '<a href="#sources">Sources</a><a href="#findings">Findings</a>'
        '<a href="#plan">NextStep plan</a><a href="#timeline">Timeline</a>'
        '<a href="#audit">Audit</a></div></nav>'
        '<main class="container"><div class="notice"><strong>Safety boundary:</strong> '
        'All records are fabricated. Missing electronic documentation is not proof of missed care. '
        'This report does not diagnose, approve, contact anyone, execute proposed source checks '
        'or update any system. An authorized human must review every administrative finding.</div>'
        '<div class="stats">' + stats_html + '</div>'
        '<div class="panel"><strong>Loaded inputs</strong><div style="margin-top:9px">' +
        guide + "</div></div>" +
        "".join(cards) +
        '<div class="footer">TB-CareOS E06 local review MVP · Generated as a self-contained '
        'HTML file. No scripts or remote resources. All model and source text is HTML-escaped. '
        'Read-only demonstration; no clinical advice.</div>'
        "</main></body></html>"
    )
