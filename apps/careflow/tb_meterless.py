"""E03: reconcile synthetic Zetaris records and persist in actual Meterless World Model.

All state is under an ignored local_data/ directory; no real patient sources.
Requires checked-out Meterless repo with npm ci completed in
engines/world-model/reference and locally configured Zetaris helper.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

from apps.careflow.reconcile import reconcile_case
from shared.meterless.mapper import to_meterless_observations
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError


ROOT = Path(__file__).resolve().parents[2]


def persist_bundle(bundle: dict, *, reference: str | Path, state_dir: str | Path) -> dict:
    ref = Path(reference).expanduser().resolve()
    executable = ref / "node_modules" / ".bin" / "tsx"
    entry = ref / "src" / "index.ts"
    bridge = ROOT / "shared" / "meterless" / "world_model_bridge.ts"
    if not entry.is_file():
        raise RuntimeError("Missing Meterless reference src/index.ts in --reference")
    if not executable.is_file():
        raise RuntimeError("Missing reference node_modules/.bin/tsx; run npm ci in its reference checkout")
    mapped = to_meterless_observations(bundle)
    try:
        completed = subprocess.run(
            [
                str(executable), str(bridge),
                "--reference", str(ref),
                "--case-id", bundle["case_id"],
                "--state-dir", str(Path(state_dir).expanduser().resolve()),
            ],
            cwd=ref,
            input=json.dumps(mapped, separators=(",", ":"), ensure_ascii=False),
            text=True, capture_output=True, encoding="utf-8", timeout=180, check=False,
            env=os.environ.copy(),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("Could not execute bounded local Meterless World Model bridge") from exc
    if completed.returncode != 0:
        raise RuntimeError("Meterless bridge failed; inspect local stderr privately (no secrets in chat)")
    try:
        result = json.loads(completed.stdout)
    except ValueError as exc:
        raise RuntimeError("Meterless bridge produced invalid JSON report") from exc
    if not result.get("replay", {}).get("projection_unchanged") or not result.get("persisted_projection_matches"):
        raise RuntimeError("World Model replay or persistence invariants failed")
    return result


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--case-id", default="CASE-TB-001", help="Fabricated TB-v1 case ID")
    p.add_argument("--namespace", default="TBCARE_OS", help="Authorized Zetaris namespace")
    p.add_argument("--helper", default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"),
                   help="Official Zetaris query_zetaris.py path")
    p.add_argument("--bundle-file", help="Load a saved evidence_bundle.v1 instead of querying Zetaris")
    p.add_argument("--reference", required=True, help="Meterless World Model reference directory")
    p.add_argument("--state-dir", default=str(ROOT / "local_data" / "meterless"),
                   help="Gitignored local persistent World Model state location")
    args = p.parse_args(argv)
    try:
        if args.bundle_file:
            with open(args.bundle_file, encoding="utf-8") as handle:
                bundle = json.load(handle)
            if bundle.get("case_id") != args.case_id:
                raise ValueError("Saved bundle case_id disagrees with requested case")
        else:
            if not args.helper:
                p.error("Provide --helper or --bundle-file")
            bundle = reconcile_case(
                ZetarisHelperClient(args.helper), namespace=args.namespace,
                case_id=args.case_id,
            )
        summary = persist_bundle(bundle, reference=args.reference, state_dir=args.state_dir)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0
    except (RuntimeError, ValueError, ZetarisQueryError, OSError) as exc:
        print("E03 integration failed: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
