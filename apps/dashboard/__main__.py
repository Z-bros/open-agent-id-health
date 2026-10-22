"""E06 local read-only coordinator dashboard over fabricated TB-CareOS records."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from apps.careflow.reconcile import reconcile_case
from apps.dashboard.render import render_dashboard
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


def _read_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("Dashboard inputs must be JSON objects")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Synthetic CASE-TB-018")
    parser.add_argument("--bundle", type=Path,
                        help="Saved fabricated evidence_bundle.v1 file")
    parser.add_argument("--namespace", default="TBCARE_OS",
                        help="Zetaris namespace for live read-only evidence")
    parser.add_argument("--helper", default=os.environ.get(
        "TB_CAREOS_ZETARIS_QUERY_HELPER"),
        help="Official read-only Zetaris helper when --bundle is omitted")
    parser.add_argument("--explanation", type=Path,
                        help="Optional verified CaseLens explanation_report.v1")
    parser.add_argument("--plan", type=Path,
                        help="Optional NextStep verification_plan.v1")
    parser.add_argument("--meterless-summary", type=Path,
                        help="Optional E03 Meterless summary JSON")
    parser.add_argument("--output", type=Path,
                        help="Local .html output; defaults to outputs/e06_<case-id>.html")
    args = parser.parse_args(argv)

    try:
        if args.bundle:
            bundle = _read_json(args.bundle)
        else:
            if not args.helper:
                parser.error("Provide --bundle or --helper")
            bundle = reconcile_case(
                ZetarisHelperClient(args.helper),
                namespace=args.namespace, case_id=args.case_id,
            )
        if bundle.get("case_id") != args.case_id:
            raise ValueError("Requested case ID does not match evidence bundle")
        explanation = _read_json(args.explanation) if args.explanation else None
        plan = _read_json(args.plan) if args.plan else None
        meterless = _read_json(args.meterless_summary) if args.meterless_summary else None
        html = render_dashboard(
            bundle,
            explanation=explanation,
            plan=plan,
            meterless_summary=meterless,
        )

        out = args.output or Path("outputs") / ("e06_" + args.case_id.lower() + ".html")
        dest = out.expanduser().resolve()
        if dest.suffix.lower() != ".html":
            raise ValueError("Dashboard --output must be .html")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(html, encoding="utf-8")
        dest.chmod(0o600)
        print(json.dumps({
            "dashboard_created": True,
            "case_id": args.case_id,
            "path": str(dest),
            "observations": len(bundle["observations"]),
            "findings": len(bundle["exceptions"]),
            "explanation_included": explanation is not None,
            "plan_included": plan is not None,
            "meterless_summary_included": meterless is not None,
            "read_only": True,
            "requires_human_approval": True,
        }, indent=2))
        return 0
    except (ValueError, TypeError, OSError, KeyError,
            ZetarisQueryError, json.JSONDecodeError) as exc:
        print(
            f"E06 dashboard failed closed: {type(exc).__name__}: {exc}",
            file=sys.stderr,
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
