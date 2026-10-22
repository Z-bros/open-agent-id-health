"""Read-only real-Zetaris evidence probe; not yet the full reconciliation agent.

Run at repo root: python3 -m apps.careflow.tb_zetaris_probe --help
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from shared.zetaris.readonly import (
    ALLOWED_SOURCES, ZetarisHelperClient, ZetarisQueryError, case_query,
)


def probe_case(client: Any, *, namespace: str, case_id: str, limit: int = 100) -> dict[str, Any]:
    """Preserve not_found separately from permission errors and source outages."""
    entries = []
    for source in ALLOWED_SOURCES:
        sql = case_query(namespace, source, case_id, limit=limit)
        try:
            rows = client.query(sql)
        except ZetarisQueryError as exc:
            entries.append({"source": source, "status": exc.category, "row_count": None,
                            "source_record_ids": []})
            continue
        ids = []
        for row in rows:
            candidate = row.get("source_record_id") or row.get("record_id")
            if candidate is not None:
                ids.append(str(candidate))
        entries.append({"source": source, "status": "available" if rows else "not_found",
                        "row_count": len(rows), "source_record_ids": ids})
    return {"case_id": case_id, "namespace": namespace, "sources": entries,
            "requires_human_approval": True,
            "note": "Synthetic records only. Missing documentation does not establish missed care."}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case-id", required=True, help="Fabricated case ID")
    p.add_argument("--namespace", required=True, help="Authorized Zetaris TB namespace")
    p.add_argument("--helper", default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
                   help="Path to zetaris/getting-started/scripts/query_zetaris.py")
    p.add_argument("--limit", type=int, default=100, help="Maximum rows per source, up to 500")
    p.add_argument("--dry-run", action="store_true", help="Show queries without invoking Zetaris")
    args = p.parse_args(argv)
    try:
        queries = {s: case_query(args.namespace, s, args.case_id, limit=args.limit)
                   for s in ALLOWED_SOURCES}
        if args.dry_run:
            print(json.dumps({"dry_run": True, "queries": queries}, indent=2))
            return 0
        if not args.helper:
            p.error("--helper or TB_CAREOS_ZETARIS_QUERY_HELPER is required for live queries")
        result = probe_case(ZetarisHelperClient(args.helper), namespace=args.namespace,
                            case_id=args.case_id, limit=args.limit)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 2 if any(s["status"] not in {"available", "not_found"} for s in result["sources"]) else 0
    except (ValueError, ZetarisQueryError) as exc:
        print(f"preflight error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
