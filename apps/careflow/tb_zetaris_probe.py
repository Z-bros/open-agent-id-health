"""Read-only Zetaris evidence probe for fabricated TB-v1 administrative records.

Run at repo root: python3 -m apps.careflow.tb_zetaris_probe --help

This is an E01 retrieval diagnostic, NOT the CareFlow reconciliation agent.
It does not apply source-check simulation or visible_from_attempt filters;
neither an empty raw table query nor an outage proves missed clinical care.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from shared.zetaris.readonly import (
    ZetarisHelperClient, ZetarisQueryError, case_query,
)

# The five evidence tables in tb_v1/README.md. source_checks.csv is a separate
# synthetic retry/test-harness input, not a patient-document evidence table.
EVIDENCE_SOURCES = (
    "cases", "screening_events", "lab_orders", "lab_results", "followup_events",
)
# Each event row has an ingest_row_id; identity is NOT a generic record_id.
PROVENANCE_IDS = {
    "cases": "case_id",
    "screening_events": "ingest_row_id",
    "lab_orders": "ingest_row_id",
    "lab_results": "ingest_row_id",
    "followup_events": "ingest_row_id",
}
BUSINESS_IDS = {
    "cases": "case_id",
    "screening_events": "event_id",
    "lab_orders": "order_id",
    "lab_results": "result_id",
    "followup_events": "followup_event_id",
}


def summarize_source_rows(rows: list[dict[str, Any]], *, source: str, case_id: str) -> dict[str, Any]:
    """Summarize source-linked identifiers, fail-closed if expected columns are absent.

    Business IDs may repeat across imports by design. ingest_row_id is the
    row-level provenance key; business identity is tracked separately.
    """
    source_ids: list[str] = []
    business_ids: list[str] = []
    for original in rows:
        row = {str(key).lower(): value for key, value in original.items()}
        if str(row.get("case_id", "")) != case_id:
            raise ZetarisQueryError(
                "invalid_response", f"{source} returned absent/mismatched case_id"
            )
        provenance = row.get(PROVENANCE_IDS[source])
        business = row.get(BUSINESS_IDS[source])
        if provenance is None or str(provenance) == "" or business is None or str(business) == "":
            raise ZetarisQueryError(
                "invalid_response", f"{source} returned a row without required evidence identity"
            )
        source_ids.append(str(provenance))
        business_ids.append(str(business))
    return {
        "source": source,
        "status": "available" if rows else "not_found",
        "row_count": len(rows),
        "source_record_ids": source_ids,
        "business_event_ids": business_ids,
    }


def probe_case(client: Any, *, namespace: str, case_id: str, limit: int = 100) -> dict[str, Any]:
    """Return raw source availability without misclassifying query failure as missing care."""
    entries = []
    for source in EVIDENCE_SOURCES:
        sql = case_query(namespace, source, case_id, limit=limit)
        try:
            rows = client.query(sql)
            entry = summarize_source_rows(rows, source=source, case_id=case_id)
        except ZetarisQueryError as exc:
            entry = {
                "source": source,
                "status": exc.category,
                "row_count": None,
                "source_record_ids": [],
                "business_event_ids": [],
            }
        entries.append(entry)
    return {
        "case_id": case_id,
        "namespace": namespace,
        "sources": entries,
        "source_check_simulation_applied": False,
        "visibility_simulation_applied": False,
        "requires_human_approval": True,
        "note": (
            "Synthetic documentation-only raw retrieval. Empty results are not proof of "
            "missed care. Source-check retry and visibility simulation are NOT applied."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case-id", required=True, help="Fabricated case ID, e.g. CASE-TB-001")
    p.add_argument("--namespace", required=True, help="Authorized Zetaris TB namespace")
    p.add_argument(
        "--helper", default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
        help="Path to official zetaris/getting-started/scripts/query_zetaris.py"
    )
    p.add_argument("--limit", type=int, default=100, help="Maximum rows per source, up to 500")
    p.add_argument("--dry-run", action="store_true", help="Show queries without invoking Zetaris")
    args = p.parse_args(argv)
    try:
        queries = {
            source: case_query(args.namespace, source, args.case_id, limit=args.limit)
            for source in EVIDENCE_SOURCES
        }
        if args.dry_run:
            print(json.dumps({"dry_run": True, "queries": queries}, indent=2))
            return 0
        if not args.helper:
            p.error("--helper or TB_CAREOS_ZETARIS_QUERY_HELPER is required for live queries")
        result = probe_case(
            ZetarisHelperClient(args.helper),
            namespace=args.namespace, case_id=args.case_id, limit=args.limit
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if any(
            entry["status"] not in {"available", "not_found"} for entry in result["sources"]
        ) else 0
    except (ValueError, ZetarisQueryError) as exc:
        print(f"preflight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
