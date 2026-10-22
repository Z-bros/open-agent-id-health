"""E03 adapter: turn source-cited synthetic evidence_bundle.v1 into World Model inputs.

No ground-truth data, no real patient records, no secrets, no write-back to Zetaris.
The TypeScript sidecar calls the actual Meterless reference WorldModel.ingest.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from typing import Any

_CASE = re.compile(r"^CASE-TB-[0-9]{3,}$")
_MAX_OBSERVATIONS = 500
_MAX_EXCEPTIONS = 100


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _timestamp(value: Any) -> str:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("Evidence timestamp must be an ISO UTC string")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid evidence timestamp") from exc
    if dt.tzinfo is None:
        raise ValueError("Timezone required")
    return dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def world_observations(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    """Normalize vetted CareFlow observations and exceptions for Meterless ingestion.

    Idempotency keys use source_row provenance; exception keys use category and
    cited business IDs, while text captures updates under the same key.
    """
    if not isinstance(bundle, dict) or bundle.get("schema_version") != "1.0.0":
        raise ValueError("Expected evidence_bundle.v1 / schema_version 1.0.0")
    case_id = bundle.get("case_id")
    if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
        raise ValueError("Only fabricated CASE-TB-* records are permitted")
    records = bundle.get("observations")
    findings = bundle.get("exceptions")
    checks = bundle.get("source_checks")
    if not isinstance(records, list) or not 0 < len(records) <= _MAX_OBSERVATIONS:
        raise ValueError("Evidence bundle needs 1–500 source observations")
    if not isinstance(findings, list) or len(findings) > _MAX_EXCEPTIONS:
        raise ValueError("Too many exceptions or invalid exceptions")
    if not isinstance(checks, list) or bundle.get("requires_human_approval") is not True:
        raise ValueError("A valid bundle must preserve source checks and human approval")

    indexed: dict[str, list[dict[str, Any]]] = {}
    converted = []
    for observation in records:
        if not isinstance(observation, dict):
            raise ValueError("Invalid observation")
        source_id = observation.get("source_record_id")
        business_id = observation.get("record_id")
        subject = observation.get("subject_ref")
        table = observation.get("record_type")
        system = observation.get("source_system")
        details = observation.get("details", {})
        if not all(isinstance(v, str) and v for v in (source_id, business_id, table, system)):
            raise ValueError("Observation missing source provenance")
        if not isinstance(subject, str) or not subject.startswith("SYN-SUBJ-"):
            raise ValueError("Non-synthetic subject reference rejected")
        if not isinstance(details, dict) or details.get("case_id") != case_id:
            raise ValueError("Cross-case or unverified observation rejected")
        when = _timestamp(observation.get("observed_at"))
        stable = f"tb-careos:{case_id}:source:{table}:{system}:{source_id}"
        entry = {
            "externalId": stable,
            "type": "tb_source_evidence",
            "title": f"{table} / {source_id}",
            "text": canonical_json({
                "case_id": case_id,
                "business_event_id": business_id,
                "source_record_id": source_id,
                "source_system": system,
                "subject_ref": subject,
                "record_type": table,
                "details": details,
            }),
            "at": when,
            "source": {"kind": "api", "by": "TB-CareFlow/Zetaris",
                       "at": when, "url": f"zetaris://{table}/{source_id}"},
            "entities": [{"type": "tb_synthetic_case", "name": case_id}],
        }
        converted.append(entry)
        indexed.setdefault(business_id, []).append(entry)

    default_at = max(x["at"] for x in converted)
    for issue in findings:
        if not isinstance(issue, dict):
            raise ValueError("Invalid exception")
        category = issue.get("category")
        cited = issue.get("evidence_record_ids")
        description = issue.get("description")
        if not isinstance(category, str) or not category or not isinstance(description, str):
            raise ValueError("Invalid exception category/description")
        if not isinstance(cited, list) or not all(isinstance(x, str) for x in cited):
            raise ValueError("Invalid exception references")
        # Reject fabricated or dangling cited IDs before archiving a finding.
        if any(ref not in indexed for ref in cited):
            raise ValueError("Exception references a non-retrieved record")
        cited_time = [x["at"] for ref in cited for x in indexed[ref]]
        at = max(cited_time, default=default_at)
        stable_key = {
            "case_id": case_id,
            "category": category,
            "evidence_record_ids": sorted(set(cited)),
        }
        suffix = hashlib.sha256(canonical_json(stable_key).encode()).hexdigest()[:20]
        converted.append({
            "externalId": f"tb-careos:{case_id}:finding:{suffix}",
            "type": "tb_admin_finding",
            "title": f"{category} / {case_id}",
            "text": canonical_json({**stable_key, "description": description,
                                     "requires_human_approval": True}),
            "at": at,
            "source": {"kind": "agent", "by": "TB-CareFlow/rule-check",
                       "at": at},
            "entities": [{"type": "tb_synthetic_case", "name": case_id}],
        })

    # Stable order makes replays canonical across source retrieval ordering.
    return sorted(converted, key=lambda item: item["externalId"])
