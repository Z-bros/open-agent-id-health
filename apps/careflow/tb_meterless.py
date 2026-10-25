"""Run E02 CareFlow evidence through the actual Meterless TypeScript World Model.

Only synthetic source-linked evidence; local persistence and read-only Zetaris.
Use a saved evidence bundle (--bundle) or query live via existing E02 adapter.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from apps.careflow.reconcile import reconcile_case
from shared.meterless.adapter import world_observations
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-id", required=True, help="Synthetic CASE-TB-001")
    parser.add_argument("--namespace", default="TBCARE_OS")
    parser.add_argument("--helper", default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
                        help="Path to official zetaris getting-started query_zetaris.py")
    parser.add_argument("--bundle", type=Path, help="Read existing evidence_bundle.v1 JSON instead of Zetaris")
    parser.add_argument("--explanation", type=Path,
                        help="Optional saved E04 validated explanation_report.v1")
    parser.add_argument("--plan", type=Path,
                        help="Optional saved E05 validated verification_plan.v1")
    parser.add_argument("--reference", type=Path, required=True,
                        help="Path to checked-out Meterless/engines/world-model/reference")
    parser.add_argument("--state-dir", type=Path, default=Path("outputs/meterless"),
                        help="Local synthetic World Model persistence directory")
    parser.add_argument("--timeout", type=int, default=120)
    args = parser.parse_args(argv)

    try:
        if args.bundle is not None:
            bundle = json.loads(args.bundle.read_text(encoding="utf-8"))
        else:
            if not args.helper:
                parser.error("--helper required unless --bundle supplied")
            bundle = reconcile_case(ZetarisHelperClient(args.helper),
                                    namespace=args.namespace, case_id=args.case_id)
        if bundle.get("case_id") != args.case_id:
            raise ValueError("Requested case does not match evidence bundle")
        explanation = (json.loads(args.explanation.read_text(encoding="utf-8"))
                       if args.explanation else None)
        plan = (json.loads(args.plan.read_text(encoding="utf-8"))
                if args.plan else None)
        if (explanation is not None and not isinstance(explanation, dict)) or (
            plan is not None and not isinstance(plan, dict)
        ):
            raise ValueError("E04/E05 artifact must be a JSON object")
        observations = world_observations(bundle, explanation=explanation, plan=plan)
        if not 10 <= args.timeout <= 300:
            raise ValueError("Timeout must be 10–300 seconds")
        ref = args.reference.expanduser().resolve()
        tsx = ref / "node_modules" / ".bin" / "tsx"
        if not (ref / "src" / "index.ts").is_file() or not tsx.is_file():
            raise ValueError("Meterless reference missing or npm ci not run under --reference")
        sidecar = Path(__file__).resolve().parents[2] / "scripts" / "meterless-world-model.mts"
        if not sidecar.is_file():
            raise ValueError("Meterless World Model sidecar missing")
        state_dir = args.state_dir.expanduser().resolve()
        state_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="tbcareos_meterless_") as temp:
            payload = Path(temp) / "observations.json"
            # Temp directory defaults to owner-only permissions on Linux.
            with payload.open("x", encoding="utf-8") as stream:
                json.dump(observations, stream, ensure_ascii=False)
            payload.chmod(0o600)
            process = subprocess.run(
                [str(tsx), str(sidecar), "--input", str(payload),
                 "--reference", str(ref), "--state-dir", str(state_dir),
                 "--case-id", args.case_id],
                capture_output=True, text=True, timeout=args.timeout,
                check=False, cwd=str(sidecar.parent.parent),
            )
        if process.returncode != 0:
            raise RuntimeError("Meterless sidecar failed; inspect local logs without disclosing secrets")
        report = json.loads(process.stdout)
        if report.get("case_id") != args.case_id or report.get("replay", {}).get("state_unchanged") is not True:
            raise RuntimeError("Invalid or non-idempotent Meterless report")
        report["input_artifact_types"] = (
            ["careflow_evidence"] +
            (["caselens_explanation"] if explanation is not None else []) +
            (["nextstep_plan"] if plan is not None else [])
        )
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, ZetarisQueryError,
            json.JSONDecodeError, subprocess.TimeoutExpired) as exc:
        print(f"Meterless audit error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
