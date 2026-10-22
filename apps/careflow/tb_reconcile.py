"""Generate evidence_bundle.v1 from live fabricated Zetaris administrative records.

Use the configured Zetaris getting-started query_zetaris.py on your own machine.
No patient system writes, no clinical actions, no holdout/score access.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from apps.careflow.reconcile import reconcile_case
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="TBCARE_OS",
                        help="Existing authorized Zetaris namespace (default: TBCARE_OS)")
    parser.add_argument("--case-id", required=True, help="Fabricated TB-v1 case ID")
    parser.add_argument(
        "--helper",
        default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
        help="Path to official zetaris/getting-started/scripts/query_zetaris.py",
    )
    parser.add_argument("--limit", default=100, type=int,
                        help="Maximum rows per source query (1–500)")
    args = parser.parse_args(argv)
    if not args.helper:
        parser.error("Provide --helper or TB_CAREOS_ZETARIS_QUERY_HELPER")

    try:
        bundle = reconcile_case(
            ZetarisHelperClient(args.helper),
            namespace=args.namespace,
            case_id=args.case_id,
            limit=args.limit,
        )
    except (ValueError, ZetarisQueryError) as exc:
        print(f"CareFlow validation failed: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(bundle, indent=2, ensure_ascii=False))
    # A valid evidence bundle still needs manual review when sources fail.
    # Nonzero status makes severe connection failures obvious in shell scripts.
    if any(check["status"] in {"temporarily_unavailable", "permission_denied", "error"}
           for check in bundle["source_checks"]):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
