"""E05 NextStep: bounded, explainable plans over fabricated TB administrative evidence.

This module PRODUCES a plan; it never executes proposed follow-up queries.
A Nemotron call may select only IDs of deterministic, allowlisted candidates.
Model text cannot introduce SQL, source names, record IDs or action types.
"""
from __future__ import annotations

import json
import re
from typing import Any

from apps.careflow.tb_zetaris_probe import EVIDENCE_SOURCES
from apps.caselens.explain import CaseLensValidationError, _context

READABLE = frozenset({"available", "not_found"})
MAX_CONTRACT_ACTIONS = 6
MAX_QUERY_ACTIONS = min(5, MAX_CONTRACT_ACTIONS - 2)  # mandatory manual_review + stop
_QUERY_SOURCES = {
    "subject_mismatch": (),
    "cross_source_link_mismatch": (),
    "duplicate_business_event_replay": (),
    "lab_document_not_found_in_query": ("lab_results",),
    "followup_document_not_found_in_query": ("followup_events",),
    "source_query_unavailable": (),
    "case_reference_unverified": (),
}
_SELECTOR_PROMPT = """You are TB-NextStep, a bounded administrative verification selector.
All records are fabricated; no clinical interpretation, patient outreach or care
recommendation is allowed. CareFlow supplies the fixed findings and permitted
query candidates. Select 1 or more query IDs ONLY from allowed_queries, up to
max_queries, ordered by administrative verification utility. Do not propose SQL,
new record IDs, sources, or operations. This plans lookups; it does NOT perform
them. Human manual review and stopping conditions are automatically attached.
Respond with strict JSON ONLY: {"selected_query_ids":["q1"]}.
No other keys, no Markdown, no explanations."""
_CASE = re.compile(r"CASE-TB-[0-9]{3,}")


class NextStepValidationError(ValueError):
    """Unsafe or unsupported evidence/plan selection; fail closed."""


def _check_explanation(bundle: dict[str, Any], explanation: dict[str, Any] | None) -> None:
    if explanation is None:
        return
    if not isinstance(explanation, dict) or set(explanation) != {
        "schema_version", "case_id", "hypotheses",
        "unresolved_questions", "requires_human_approval",
    } or explanation["schema_version"] != "1.0.0" or (
        explanation["case_id"] != bundle["case_id"]
    ) or explanation["requires_human_approval"] is not True:
        raise NextStepValidationError("Explanation report contract/case mismatch")
    hypotheses = explanation["hypotheses"]
    questions = explanation["unresolved_questions"]
    if not isinstance(hypotheses, list) or not isinstance(questions, list):
        raise NextStepValidationError("Invalid explanation report lists")
    if len(hypotheses) != len(bundle["exceptions"]) or (
        not all(isinstance(q, str) and 0 < len(q) <= 220 for q in questions)
    ):
        raise NextStepValidationError("Explanation findings or questions invalid")
    allowed = [
        (
            "Administrative review finding: " + f["category"],
            set(f["evidence_record_ids"]),
        )
        for f in bundle["exceptions"]
    ]
    observed = []
    for h in hypotheses:
        if not isinstance(h, dict) or set(h) != {
            "hypothesis", "assessment", "reason", "evidence_record_ids",
        } or h["assessment"] not in {"supported", "unresolved", "contradicted"} or (
            not isinstance(h["reason"], str)
        ) or not isinstance(h["evidence_record_ids"], list):
            raise NextStepValidationError("Invalid explanation hypothesis")
        if not all(isinstance(x, str) for x in h["evidence_record_ids"]):
            raise NextStepValidationError("Invalid explanation evidence IDs")
        observed.append((h["hypothesis"], set(h["evidence_record_ids"])))
    if sorted(observed, key=str) != sorted(allowed, key=str):
        raise NextStepValidationError("Explanation contradicts CareFlow finding identities")


def _source_checks(bundle: dict[str, Any]) -> dict[str, str]:
    statuses: dict[str, tuple[int, str]] = {}
    for check in bundle["source_checks"]:
        table = check["source_system"]
        attempt = check.get("attempt")
        if table not in EVIDENCE_SOURCES or (
            type(attempt) is not int or attempt < 1
        ):
            raise NextStepValidationError("Unrecognized source or attempt")
        prior = statuses.get(table)
        if prior is None or attempt > prior[0]:
            statuses[table] = (attempt, check["status"])
        elif attempt == prior[0] and check["status"] != prior[1]:
            raise NextStepValidationError("Conflicting source statuses for same attempt")
    return {table: status for table, (_, status) in statuses.items()}


def _candidates(bundle: dict[str, Any], source_statuses: dict[str, str]) -> list[dict[str, Any]]:
    observations = bundle["observations"]
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()

    def consider(table: str, refs: list[str], category: str) -> None:
        # Do not recommend retrying a forbidden/unavailable source or one
        # whose status is absent. Never propose a lookup in unknown tables.
        if table not in EVIDENCE_SOURCES or source_statuses.get(table) not in READABLE:
            return
        ids = sorted(set(refs))
        key = (table, tuple(ids))
        if key in seen:
            return
        seen.add(key)
        reason = (
            f"Bounded read-only verification in {table} for {category}; "
            "compare only the retrieved synthetic administrative evidence. "
        )
        if source_statuses[table] == "not_found":
            reason += "Earlier query returned no row; absence of documentation is unverified."
        else:
            reason += "Retrieved identifiers may require cross-source comparison."
        candidates.append({
            "query_id": "q" + str(len(candidates) + 1),
            "action": "read_only_source_query",
            "source_system": table,
            "reason": reason,
            "evidence_record_ids": ids,
            "finding_category": category,
        })

    for finding in bundle["exceptions"]:
        category = finding["category"]
        refs = finding["evidence_record_ids"]
        for table in _QUERY_SOURCES[category]:
            consider(table, refs, category)
        if category in {
            "subject_mismatch", "cross_source_link_mismatch",
            "duplicate_business_event_replay",
        }:
            # Only sources tied to actual cited records; no invented lookups.
            for table in EVIDENCE_SOURCES:
                if any(
                    o["record_id"] in refs and o["record_type"] == table
                    for o in observations
                ):
                    consider(table, refs, category)
        if len(candidates) >= 20:
            break
    return candidates[:20]


def _validate_selection(raw: str, candidates: list[dict[str, Any]], cap: int) -> list[str]:
    try:
        selected = json.loads(raw)
    except (ValueError, TypeError) as exc:
        raise NextStepValidationError("Nemotron selection was not strict JSON") from exc
    if not isinstance(selected, dict) or set(selected) != {"selected_query_ids"}:
        raise NextStepValidationError("Nemotron tried to output unsupported plan fields")
    ids = selected["selected_query_ids"]
    if not isinstance(ids, list) or not 1 <= len(ids) <= cap or (
        not all(isinstance(x, str) for x in ids)
    ) or len(set(ids)) != len(ids):
        raise NextStepValidationError("Nemotron query selection violates bounds")
    permitted = {c["query_id"] for c in candidates}
    if any(x not in permitted for x in ids):
        raise NextStepValidationError("Nemotron selected a non-allowlisted query")
    return ids


def validate_plan(bundle: dict[str, Any], plan: dict[str, Any]) -> None:
    """Independent deterministic critic of the assembled v1 contract."""
    _context(bundle)
    if not isinstance(plan, dict) or set(plan) != {
        "schema_version", "case_id", "max_queries",
        "actions", "requires_human_approval",
    } or plan["schema_version"] != "1.0.0" or (
        plan["case_id"] != bundle["case_id"]
    ) or plan["requires_human_approval"] is not True:
        raise NextStepValidationError("Plan contract or case invalid")
    cap = plan["max_queries"]
    actions = plan["actions"]
    if type(cap) is not int or not 0 <= cap <= MAX_QUERY_ACTIONS:
        raise NextStepValidationError("Query cap exceeds effective contract bound")
    if not isinstance(actions, list) or not 2 <= len(actions) <= MAX_CONTRACT_ACTIONS:
        raise NextStepValidationError("Plan action count invalid")
    if [x.get("action") for x in actions[-2:]] != ["manual_review", "stop"]:
        raise NextStepValidationError("Plan must end with human review and stop")
    refs = {o["record_id"] for o in bundle["observations"]}
    statuses = _source_checks(bundle)
    queries = 0
    seen = set()
    for action in actions:
        if not isinstance(action, dict) or not set(action) <= {
            "action", "reason", "source_system", "evidence_record_ids",
        } or not {"action", "reason", "evidence_record_ids"} <= set(action):
            raise NextStepValidationError("Unknown action field or required field missing")
        if action["action"] not in {
            "read_only_source_query", "manual_review", "stop",
        } or not isinstance(action["reason"], str) or (
            not 20 <= len(action["reason"]) <= 650
        ) or not isinstance(action["evidence_record_ids"], list) or (
            not all(isinstance(x, str) for x in action["evidence_record_ids"])
        ) or set(action["evidence_record_ids"]) - refs:
            raise NextStepValidationError("Action contains unsupported record reference")
        if action["action"] == "read_only_source_query":
            queries += 1
            source = action.get("source_system")
            key = (source, tuple(action["evidence_record_ids"]))
            if source not in EVIDENCE_SOURCES or statuses.get(source) not in READABLE:
                raise NextStepValidationError("Read-only query uses forbidden/unavailable source")
            if key in seen:
                raise NextStepValidationError("Repeated query in the same plan")
            seen.add(key)
        elif "source_system" in action:
            raise NextStepValidationError("Non-query action specifies a source")
    if any(a["action"] != "read_only_source_query" for a in actions[:-2]) or queries > cap:
        raise NextStepValidationError("Plan violates bounded-action order or query cap")


def plan_case(
    bundle: dict[str, Any], *,
    model_client: Any | None = None,
    explanation: dict[str, Any] | None = None,
    max_queries: int = 3,
) -> dict[str, Any]:
    """Assemble a plan without executing its proposed queries or human actions.

    model_client=None is an explicitly offline, deterministic planning baseline.
    With a real client, Nemotron chooses only among already-permitted query IDs.
    A failed/malformed model response does NOT silently fall back to offline.
    """
    try:
        _context(bundle)
    except CaseLensValidationError as exc:
        raise NextStepValidationError(str(exc)) from exc
    if type(max_queries) is not int or not 0 <= max_queries <= MAX_QUERY_ACTIONS:
        raise NextStepValidationError("max_queries must be 0–4 for the v1 schema")
    _check_explanation(bundle, explanation)
    statuses = _source_checks(bundle)
    candidates = _candidates(bundle, statuses)
    cap = min(max_queries, len(candidates))
    if cap and model_client is not None:
        request = {
            "case_id": bundle["case_id"],
            "max_queries": cap,
            "allowed_queries": [{
                "query_id": c["query_id"],
                "source_system": c["source_system"],
                "evidence_record_ids": c["evidence_record_ids"],
                "finding_category": c["finding_category"],
            } for c in candidates],
        }
        # No arbitrary source descriptions or CaseLens free text in the model
        # prompt. Only synthetic bounded candidate IDs and statuses.
        selected_ids = _validate_selection(
            model_client.complete([
                {"role": "system", "content": _SELECTOR_PROMPT},
                {"role": "user", "content": "ALLOWED CANDIDATES:\n" + json.dumps(request)},
            ]),
            candidates, cap,
        )
    else:
        selected_ids = [c["query_id"] for c in candidates[:cap]]

    choices = {c["query_id"]: c for c in candidates}
    actions: list[dict[str, Any]] = []
    for cid in selected_ids:
        item = choices[cid]
        actions.append({
            "action": "read_only_source_query",
            "source_system": item["source_system"],
            "reason": item["reason"],
            "evidence_record_ids": item["evidence_record_ids"],
        })
    affected_ids = sorted({
        ref for finding in bundle["exceptions"]
        for ref in finding["evidence_record_ids"]
    })
    if bundle["exceptions"]:
        manual_reason = (
            "A human reviewer must resolve these administrative evidence discrepancies, "
            "including any source unavailability; no diagnosis, missing-care claim, "
            "patient contact, or record change is authorized."
        )
    else:
        manual_reason = (
            "No CareFlow exception was detected, but the source snapshot may be incomplete; "
            "a human reviewer must assess evidence sufficiency before concluding anything."
        )
    actions.extend([
        {
            "action": "manual_review",
            "reason": manual_reason,
            "evidence_record_ids": affected_ids,
        },
        {
            "action": "stop",
            "reason": (
                "Stop at the bounded plan. Do not execute additional queries automatically; "
                "do not write to any system, contact patients, infer care outcomes, or "
                "approve an administrative action without a human reviewer."
            ),
            "evidence_record_ids": [],
        },
    ])
    plan = {
        "schema_version": "1.0.0",
        "case_id": bundle["case_id"],
        "max_queries": max_queries,
        "actions": actions,
        "requires_human_approval": True,
    }
    validate_plan(bundle, plan)
    return plan
