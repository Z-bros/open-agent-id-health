"""Post-kickoff TB-CareFlow administrative evidence reconciliation.

Converts read-only Zetaris results to the pre-existing evidence_bundle.v1
contract. This deterministic first pass does not use ground-truth holdouts,
simulate source_checks.csv, or autonomously decide clinical care.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from apps.careflow.tb_zetaris_probe import (
    BUSINESS_IDS, EVIDENCE_SOURCES, PROVENANCE_IDS,
    summarize_source_rows,
)
from shared.zetaris.readonly import ZetarisQueryError, case_query

TIMESTAMPS = {
    "cases": "opened_at",
    "screening_events": "recorded_at",
    "lab_orders": "ordered_at",
    "lab_results": "released_at",
    "followup_events": "documented_at",
}
REFERENCE_FIELDS = {
    "screening_events": ("linked_order_id",),
    "lab_orders": ("screening_event_id",),
    "lab_results": ("order_id",),
    "followup_events": ("order_id", "result_id"),
}
SCHEMA_STATUSES = {"available", "not_found", "temporarily_unavailable", "permission_denied", "error"}


def _as_time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ZetarisQueryError("invalid_response", "Missing or non-UTC fabricated event timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ZetarisQueryError("invalid_response", "Malformed fabricated event timestamp") from exc
    return parsed


def _normalize(row: dict[str, Any]) -> dict[str, Any]:
    return {str(k).lower(): v for k, v in row.items()}


def _observation(table: str, original: dict[str, Any], case_id: str) -> dict[str, Any]:
    row = _normalize(original)
    if str(row.get("case_id")) != case_id:
        raise ZetarisQueryError("invalid_response", "Case mismatch in source row")
    provenance = row.get(PROVENANCE_IDS[table])
    business = row.get(BUSINESS_IDS[table])
    person = row.get("subject_ref")
    at = row.get(TIMESTAMPS[table])
    if not all(x is not None and str(x).strip() for x in (provenance, business, person, at)):
        raise ZetarisQueryError("invalid_response", "Required provenance, subject, or timestamp absent")
    _as_time(at)
    details: dict[str, Any] = {"case_id": case_id, "source_table": table}
    for field in REFERENCE_FIELDS.get(table, ()):
        if row.get(field):
            details[field] = str(row[field])
    # Metadata only; no clinical outcome values or tokens are copied.
    for field in ("ingested_at", "visible_from_attempt"):
        if row.get(field) is not None:
            details[field] = str(row[field])
    return {
        "record_id": str(business),
        "source_system": str(row.get("source_system") or "CASES_SIM"),
        "source_record_id": str(provenance),
        "subject_ref": str(person),
        "record_type": table,
        "observed_at": str(at),
        "details": details,
    }


def _exception(category: str, description: str, observations: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "category": category,
        "description": description,
        "evidence_record_ids": sorted({x["record_id"] for x in observations}),
    }


def reconcile_case(
    client: Any, *, namespace: str, case_id: str, limit: int = 100
) -> dict[str, Any]:
    """Read all five registered Zetaris evidence tables, retaining per-source errors.

    Missing documentation is treated as *unverified*, not proof of missed care.
    No simulated source snapshot/completeness is applied in this first pass.
    """
    rows: dict[str, list[dict[str, Any]]] = {}
    statuses: dict[str, str] = {}
    observations: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    exceptions: list[dict[str, Any]] = []

    for table in EVIDENCE_SOURCES:
        query = case_query(namespace, table, case_id, limit=limit)
        try:
            returned = client.query(query)
            # Verify the same keys and case ID as the separately proven probe.
            summarize_source_rows(returned, source=table, case_id=case_id)
            converted = [_observation(table, item, case_id) for item in returned]
            converted.sort(key=lambda item: item["source_record_id"])
            status = "available" if returned else "not_found"
            rows[table] = [_normalize(item) for item in returned]
            observations.extend(converted)
        except ZetarisQueryError as exc:
            status = exc.category if exc.category in SCHEMA_STATUSES else "error"
            rows[table] = []
            exceptions.append(_exception(
                "source_query_unavailable",
                f"{table}: query failed ({status}); documentation status is unknown, needs human verification.",
                [],
            ))
        statuses[table] = status
        checks.append({"source_system": table, "attempt": 1, "status": status})

    case_rows = rows["cases"]
    if statuses["cases"] != "available" or len(case_rows) != 1:
        exceptions.append(_exception(
            "case_reference_unverified",
            "One unambiguous synthetic case registry row is required; no absence-of-care conclusion.",
            [],
        ))
    else:
        ref = str(case_rows[0]["subject_ref"])
        for obs in observations:
            if obs["record_type"] != "cases" and obs["subject_ref"] != ref:
                exceptions.append(_exception(
                    "subject_mismatch",
                    f"{obs['record_type']}: subject identifier conflicts with case registry; requires human review.",
                    [obs, next(x for x in observations if x["record_type"] == "cases")],
                ))

        # Only compare associations when the target source has actual rows.
        order_ids = {str(row["order_id"]) for row in rows["lab_orders"]}
        result_ids = {str(row["result_id"]) for row in rows["lab_results"]}
        screening_ids = {str(row["event_id"]) for row in rows["screening_events"]}
        associations = (
            ("screening_events", "linked_order_id", "lab_orders", order_ids),
            ("lab_orders", "screening_event_id", "screening_events", screening_ids),
            ("lab_results", "order_id", "lab_orders", order_ids),
            ("followup_events", "order_id", "lab_orders", order_ids),
            ("followup_events", "result_id", "lab_results", result_ids),
        )
        for src, field, target, valid_ids in associations:
            if statuses[target] != "available":
                continue
            for row in rows[src]:
                if row.get(field) and str(row[field]) not in valid_ids:
                    matching = [
                        x for x in observations
                        if x["record_type"] == src
                        and x["source_record_id"] == str(row[PROVENANCE_IDS[src]])
                    ]
                    exceptions.append(_exception(
                        "cross_source_link_mismatch",
                        f"{src}.{field} does not match a returned {target} ID; source linkage requires verification.",
                        matching,
                    ))

        # A raw successful empty SQL query does not certify a complete source
        # snapshot: use "not found in query", never "missing care".
        case_row = case_rows[0]
        cutoff = _as_time(case_row.get("review_cutoff_at"))
        missing_rules = (
            ("lab_results", "lab_orders", "admin_result_expected_by", "lab_document_not_found_in_query"),
            ("followup_events", "lab_results", "admin_followup_expected_by", "followup_document_not_found_in_query"),
        )
        for missing, prerequisite, due_key, category in missing_rules:
            if statuses[missing] != "not_found" or statuses[prerequisite] != "available":
                continue
            if cutoff < _as_time(case_row.get(due_key)):
                continue
            anchors = [x for x in observations if x["record_type"] == prerequisite]
            exceptions.append(_exception(
                category,
                f"{missing}: no row returned for case at this read. Source snapshot completeness "
                "has not been verified; documentation may exist elsewhere or arrive later.",
                anchors,
            ))

    # Distinguish duplicate imported provenance from repeated business IDs.
    for table in EVIDENCE_SOURCES[1:]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for obs in observations:
            if obs["record_type"] == table:
                grouped.setdefault(obs["record_id"], []).append(obs)
        for group in grouped.values():
            if len({x["source_record_id"] for x in group}) > 1:
                exceptions.append(_exception(
                    "duplicate_business_event_replay",
                    f"{table}: duplicate business ID with distinct ingestion rows; review for replay, "
                    "do not count as independent events.",
                    group,
                ))

    return {
        "schema_version": "1.0.0",
        "case_id": case_id,
        "observations": observations,
        "exceptions": exceptions,
        "source_checks": checks,
        "requires_human_approval": True,
    }
