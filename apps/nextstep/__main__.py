"""E05 NextStep CLI: saved evidence or read-only Zetaris -> bounded plan.

No proposed follow-up query is executed and no patient/system is contacted.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from apps.careflow.reconcile import reconcile_case
from apps.nextstep.plan import NextStepValidationError, plan_case
from shared.inference.nemotron import NVIDIAChatClient, NemotronError
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Fabricated CASE-TB-018")
    parser.add_argument("--bundle", type=Path, help="Saved synthetic evidence_bundle.v1")
    parser.add_argument("--explanation", type=Path, help="Optional CaseLens explanation_report.v1")
    parser.add_argument("--namespace", default="TBCARE_OS",
                        help="Existing registered synthetic Zetaris namespace")
    parser.add_argument("--helper",
                        default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
                        help="Path to the official read-only Zetaris query helper")
    parser.add_argument("--model", default=os.environ.get(
        "NEMOTRON_MODEL", "nvidia/nemotron-3.5-lightning-30b-a3b"
    ), help="Authorized NVIDIA Nemotron model ID")
    parser.add_argument("--max-queries", type=int, default=3, help="0–4 proposed lookups")
    parser.add_argument("--offline", action="store_true",
                        help="Explicit deterministic baseline; no Nemotron call")
    parser.add_argument("--output", type=Path,
                        help="Optional ignored JSON output, chmod 0600")
    args = parser.parse_args(argv)
    try:
        if args.bundle:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        else:
            if not args.helper:
                parser.error("Provide --bundle or --helper")
            bundle = reconcile_case(
                ZetarisHelperClient(args.helper),
                namespace=args.namespace, case_id=args.case_id,
            )
        if bundle.get("case_id") != args.case_id:
            raise NextStepValidationError("Requested case ID does not match bundle")
        explanation = (
            json.loads(args.explanation.read_text(encoding="utf-8"))
            if args.explanation else None
        )
        client = None if args.offline else NVIDIAChatClient(model=args.model)
        plan = plan_case(
            bundle, model_client=client,
            explanation=explanation, max_queries=args.max_queries,
        )
        formatted = json.dumps(plan, indent=2, ensure_ascii=False) + "\n"
        if args.output:
            destination = args.output.expanduser().resolve()
            if destination.suffix.lower() != ".json":
                raise ValueError("--output requires a .json path")
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(formatted, encoding="utf-8")
            destination.chmod(0o600)
        print(formatted, end="")
        return 0
    except (NextStepValidationError, NemotronError, ValueError, KeyError,
            TypeError, OSError, ZetarisQueryError, json.JSONDecodeError) as exc:
        print(f"NextStep E05 failed closed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
