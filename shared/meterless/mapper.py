"""Map evidence_bundle.v1 to Meterless World Model IngestObservation records.

This module never reads dataset oracle labels or real clinical information.
External IDs and event text are deterministic; replay preserves projection.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
from typing import Any


def _canon(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _iso(raw: str) -> str:
    if not isinstance(raw, str) or not raw.endswith("Z"):
        raise ValueError("Provenance timestamp must be an ISO UTC timestamp")
    try:
        datetime.fromisoformat(raw[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("Invalid provenance timestamp") from exc
    return raw


def to_meterless_observations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert one contract-shaped synthetic evidence bundle to Meterless inputs.

    The investigation summary is anchored to the latest *source event time*,
    NOT presented as the current verification time; true query-at timestamp
    isn't available in the v1 source_checks contract.
    """
    if bundle.get("schema_version") != "1.0.0" or bundle.get("requires_human_approval") is not True:
        raise ValueError("Expected human-review evidence_bundle.v1")
    case = bundle.get("case_id")
    if not isinstance(case, str) or not case.startswith("CASE-TB-"):
        raise ValueError("Only synthetic TB-v1 case identities are allowed")
    source_items = bundle.get("observations")
    checks = bundle.get("source_checks")
    errors = bundle.get("exceptions")
    if not isinstance(source_items, list) or not isinstance(checks, list) or not isinstance(errors, list):
        raise ValueError("Invalid evidence bundle structure")

    mapped = []
    seen = set()
    for item in source_items:
        for key in ("record_id", "record_type", "source_record_id", "source_system",
                    "subject_ref", "observed_at"):
            if not isinstance(item.get(key), str) or not item[key]:
                raise ValueError("Incomplete evidence provenance")
        if item.get("details", {}).get("case_id") != case:
            raise ValueError("Observation belongs to a different case")
        timestamp = _iso(item["observed_at"])
        evidence_id = "tbcareos:" + case + ":evidence:" + item["record_type"] + ":" + item["source_record_id"]
        if evidence_id in seen:
            raise ValueError("Duplicate evidence provenance key")
        seen.add(evidence_id)
        description = {
            "case_id": case,
            "record_id": item["record_id"],
            "record_type": item["record_type"],
            "source_system": item["source_system"],
            "source_record_id": item["source_record_id"],
            "subject_ref": item["subject_ref"],
            "details": item.get("details", {}),
        }
        mapped.append({
            "externalId": evidence_id,
            "type": "tb_evidence",
            "title": item["record_type"] + ":" + item["record_id"],
            "text": _canon(description),
            "at": timestamp,
            "source": {"kind": "pipeline", "by": "TB-CareFlow",
                       "at": timestamp, "runId": "tbcareos:" + case},
            "entities": [{"type": "tb_case", "name": case}],
        })

    # An investigation report is separate from source evidence and is marked
    # as a *derived summary* (not a new source row or a real-time event).
    anchor = max((item["at"] for item in mapped), default="1970-01-01T00:00:00Z")
    summary = {
        "case_id": case,
        "kind": "derived_investigation_summary",
        "timestamp_basis": "latest_source_observation_not_query_time",
        "source_checks": checks,
        "exceptions": errors,
        "requires_human_approval": True,
    }
    digest = hashlib.sha256(_canon(summary).encode("utf-8")).hexdigest()[:24]
    mapped.append({
        "externalId": "tbcareos:" + case + ":investigation:" + digest,
        "type": "tb_investigation",
        "title": "Administrative verification snapshot for " + case,
        "text": _canon(summary),
        "at": anchor,
        "source": {"kind": "pipeline", "by": "TB-CareFlow",
                   "at": anchor, "runId": "tbcareos:" + case},
        "entities": [{"type": "tb_case", "name": case}],
    })
    return sorted(mapped, key=lambda event: (event["at"], event["externalId"]))
