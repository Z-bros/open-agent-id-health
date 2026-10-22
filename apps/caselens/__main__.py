"""E04 CaseLens: live Zetaris -> CareFlow -> NVIDIA Nemotron -> explanation_report.v1.

No medical recommendations, patient outreach, ground-truth labels or writes
to Zetaris. See apps/caselens/README.md.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from apps.careflow.reconcile import reconcile_case
from apps.caselens.explain import CaseLensValidationError, describe_case
from shared.inference.nemotron import NVIDIAChatClient, NemotronError
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Fabricated CASE-TB-018")
    parser.add_argument("--namespace", default="TBCARE_OS",
                        help="Existing registered synthetic Zetaris namespace")
    parser.add_argument("--helper",
                        default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
                        help="Path to official read-only Zetaris query helper")
    parser.add_argument("--bundle", type=Path,
                        help="Standalone: load saved evidence_bundle.v1 instead of querying Zetaris")
    parser.add_argument("--model", default=os.environ.get(
        "NEMOTRON_MODEL", "nvidia/nemotron-3-super-120b-a12b"
    ), help="NVIDIA Build Nemotron model ID")
    parser.add_argument("--output", type=Path, help="Optional ignored output JSON file")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show finding count and status without model inference")
    args = parser.parse_args(argv)

    try:
        if args.bundle:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        else:
            if not args.helper:
                parser.error("Provide --helper or --bundle")
            bundle = reconcile_case(ZetarisHelperClient(args.helper),
                                    namespace=args.namespace, case_id=args.case_id)
        if bundle.get("case_id") != args.case_id:
            raise CaseLensValidationError("Requested case does not match source bundle")
        if args.dry_run:
            # No model, no API token, no implied explanation.
            print(json.dumps({
                "dry_run": True,
                "case_id": args.case_id,
                "observations": len(bundle["observations"]),
                "finding_categories": [x["category"] for x in bundle["exceptions"]],
                "model_requested": args.model,
                "nemotron_called": False,
            }, indent=2))
            return 0
        report = describe_case(bundle, NVIDIAChatClient(model=args.model))
        formatted = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            destination = args.output.expanduser().resolve()
            # Do not allow overwrite outside explicit local JSON output.
            if destination.suffix.lower() != ".json":
                raise ValueError("--output requires a .json path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(formatted, encoding="utf-8")
            destination.chmod(0o600)
        print(formatted, end="")
        return 0
    except (CaseLensValidationError, NemotronError, ValueError, KeyError,
            OSError, ZetarisQueryError, json.JSONDecodeError) as exc:
        # Never print raw HTTP request bodies, credentials, or model responses.
        print(f"CaseLens E04 failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
