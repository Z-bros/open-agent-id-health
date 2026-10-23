"""E09: deterministic evaluation across fabricated TB evidence cases.

This is a *process/contract integrity* evaluation, not measured clinical
accuracy or supervised exception precision/recall. It never loads the
holdout answer key, makes NVIDIA requests, or performs data mutations.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from apps.careflow.reconcile import reconcile_case
from apps.careflow.tb_zetaris_probe import EVIDENCE_SOURCES
from apps.caselens.explain import _context
from apps.nextstep.plan import plan_case, validate_plan
from shared.zetaris.readonly import ZetarisHelperClient

CASE_IDS = tuple(f"CASE-TB-{n:03d}" for n in range(1, 37))
_CASE = re.compile(r"^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$")
STATUS = frozenset((
    "available", "not_found", "temporarily_unavailable", "permission_denied", "error"
))
# A loss of access, or a syntactically corrupt record, is NOT a negative
# evidence assertion and is never counted as successful coverage.
NOT_ACCESSIBLE = frozenset(("temporarily_unavailable", "permission_denied", "error"))
NONCLINICAL_WORDS = re.compile(
    r"(?i)\b(?:diagnos(?:is|ed|e)|prescri(?:ption|bed|be)|"
    r"missed\s+(?:care|treatment)|patient\s+contact)\b"
)


def evaluate_bundle(bundle: dict[str, Any], expected_case_id: str) -> dict[str, Any]:
    """Audit one retrieved case; fail closed and do not classify care outcomes."""
    if not isinstance(expected_case_id, str) or not _CASE.fullmatch(expected_case_id):
        raise ValueError("Only CASE-TB-001 through CASE-TB-036 are authorized")
    if not isinstance(bundle, dict) or bundle.get("case_id") != expected_case_id:
        raise ValueError("The supplied bundle is cross-case or invalid")

    observations = bundle.get("observations")
    exceptions = bundle.get("exceptions")
    checks = bundle.get("source_checks")
    if not isinstance(observations, list) or not isinstance(exceptions, list) or (
        not isinstance(checks, list)
    ) or bundle.get("requires_human_approval") is not True or (
        bundle.get("schema_version") != "1.0.0"
    ):
        raise ValueError("Evidence contract invalid or human-review boundary absent")
    if len(checks) < 1 or len(checks) > 50:
        raise ValueError("Missing or unbounded source checks")
    # The live adapter makes exactly one first-pass query to each source.
    names = [item.get("source_system") for item in checks if isinstance(item, dict)]
    if names != list(EVIDENCE_SOURCES):
        raise ValueError("Five expected source checks absent or out of order")
    if any(
        set(check) != {"source_system", "attempt", "status"} or
        type(check["attempt"]) is not int or check["attempt"] != 1 or
        check["status"] not in STATUS
        for check in checks
    ):
        raise ValueError("Source check does not represent a first read with known status")

    # A source may be unreachable while other sources are returned, so do
    # not count it as a complete evidence snapshot.
    statuses = {check["source_system"]: check["status"] for check in checks}
    inaccessible = [name for name in EVIDENCE_SOURCES if statuses[name] in NOT_ACCESSIBLE]
    found = {obs.get("record_id") for obs in observations if isinstance(obs, dict)}
    if not all(isinstance(ref, str) and ref for ref in found):
        raise ValueError("Source observation identifiers must be strings")
    dangling = []
    category_counts: Counter[str] = Counter()
    for issue in exceptions:
        if not isinstance(issue, dict) or set(issue) != {
            "category", "description", "evidence_record_ids"
        } or not isinstance(issue["category"], str) or not isinstance(issue["description"], str) or (
            not isinstance(issue["evidence_record_ids"], list)
        ):
            raise ValueError("Unexpected or malformed administrative finding")
        category_counts[issue["category"]] += 1
        if NONCLINICAL_WORDS.search(issue["description"]):
            raise ValueError("Administrative finding contains unsupported clinical language")
        dangling.extend(ref for ref in issue["evidence_record_ids"] if ref not in found)
    if dangling:
        raise ValueError("Administrative finding cites unretrieved business IDs")

    result: dict[str, Any] = {
        "case_id": expected_case_id,
        "source_checks": statuses,
        "observation_count": len(observations),
        "findings_by_category": dict(sorted(category_counts.items())),
        "finding_count": len(exceptions),
        "citation_integrity": True,
        "missing_evidence_interpretation": "unverified",
        "requires_human_approval": True,
        "provider_calls": 0,
        "automatic_actions_executed": 0,
        "heldout_labels_used": False,
    }
    if not observations:
        # A zero-record case cannot be called a passed investigation.
        result.update({
            "status": "blocked_no_evidence",
            "offline_plan_validated": False,
            "plan_query_count": 0,
        })
        return result

    # Grounding checks accept only records that genuinely exist in this case.
    _context(bundle)
    plan = plan_case(bundle)  # explicitly deterministic offline / NO MODEL
    validate_plan(bundle, plan)
    actions = plan["actions"]
    if plan["case_id"] != expected_case_id or actions[-2]["action"] != "manual_review" or (
        actions[-1]["action"] != "stop"
    ) or plan["requires_human_approval"] is not True or any(
        action["action"] not in {"read_only_source_query", "manual_review", "stop"}
        for action in actions
    ):
        raise ValueError("Unsafe or unbounded plan detected")
    result.update({
        "status": "source_access_impaired" if inaccessible else "evaluated",
        "offline_plan_validated": True,
        "plan_query_count": sum(a["action"] == "read_only_source_query" for a in actions),
        "inaccessible_sources": inaccessible,
    })
    return result


def build_report(case_ids: list[str], retrieve) -> dict[str, Any]:
    """Retrieve individually; preserve failures rather than dropping cases."""
    if not isinstance(case_ids, list) or not case_ids or len(case_ids) > 36 or (
        any(not isinstance(cid, str) or not _CASE.fullmatch(cid) for cid in case_ids)
    ) or len(set(case_ids)) != len(case_ids):
        raise ValueError("Select distinct known fabricated cases only")
    cases: list[dict[str, Any]] = []
    for cid in case_ids:
        try:
            bundle = retrieve(cid)
            result = evaluate_bundle(bundle, cid)
            cases.append(result)
        except Exception as exc:
            # Never include provider/raw query errors in exported report; they
            # may carry tokens. Type-only diagnostics are intentionally safe.
            cases.append({
                "case_id": cid,
                "status": "failed_validation_or_read",
                "failure_category": type(exc).__name__,
                "provider_calls": 0,
                "automatic_actions_executed": 0,
                "heldout_labels_used": False,
            })
    statuses = Counter(result["status"] for result in cases)
    valid = [result for result in cases if result.get("offline_plan_validated")]
    categories: Counter[str] = Counter()
    source_counts: Counter[str] = Counter()
    for result in valid:
        categories.update(result["findings_by_category"])
        source_counts.update(
            (name + ":" + status for name, status in result["source_checks"].items())
        )
    n = len(cases)
    total_proposals = sum(result["plan_query_count"] for result in valid)
    return {
        "schema_version": "1.0.0",
        "assessment_kind": "synthetic_administrative_contract_and_workflow_integrity",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cases_requested": n,
        "cases_accounted_for": len(cases),
        "cases_evaluated_with_valid_plans": len(valid),
        "cases_fully_readable_and_evaluated": statuses["evaluated"],
        "cases_with_impaired_source_access": statuses["source_access_impaired"],
        "cases_blocked_no_evidence": statuses["blocked_no_evidence"],
        "cases_failed_validation_or_read": statuses["failed_validation_or_read"],
        "findings_by_category": dict(sorted(categories.items())),
        "source_read_outcomes": dict(sorted(source_counts.items())),
        "total_proposed_checks_not_executed": total_proposals,
        "human_review_required_for_valid_plans": all(
            result["requires_human_approval"] for result in valid
        ),
        "model_calls": 0,
        "source_mutations": 0,
        "proposed_checks_executed": 0,
        "ground_truth_holdout_used": False,
        "limitations": [
            "No exception detection accuracy, precision, recall or clinical validity is claimed.",
            "No patient data, ground-truth holdout, Nemotron inference, or action execution was used.",
            "A not_found source read is not proof of missing care or of snapshot completeness.",
            "Source query errors remain classified separately and are not considered clean evaluations.",
            "Model hallucination/citation fidelity still requires a separately designed LLM evaluation.",
        ],
        "case_results": cases,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--namespace", default="TBCARE_OS")
    parser.add_argument("--helper", default=os.environ.get("TB_CAREOS_ZETARIS_QUERY_HELPER"))
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--all", action="store_true", help="Evaluate 36 fabricated cases")
    scope.add_argument("--case-ids", nargs="+", metavar="CASE-TB-NNN")
    scope.add_argument("--bundle", type=Path, help="Saved evidence bundle of a single case")
    parser.add_argument("--output", type=Path, default=Path("outputs/e09_evaluation.json"))
    args = parser.parse_args(argv)
    if not args.bundle and not args.helper:
        parser.error("--helper is required for Zetaris reads")
    if args.bundle:
        try:
            content = json.loads(args.bundle.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            parser.error("Saved synthetic bundle could not be read")
        if not isinstance(content, dict) or content.get("case_id") not in CASE_IDS:
            parser.error("Saved bundle must specify an allowlisted synthetic case")
        selected = [content["case_id"]]
        retrieval = lambda cid: content
    else:
        selected = list(CASE_IDS) if args.all else list(args.case_ids)
        if any(cid not in CASE_IDS for cid in selected) or len(set(selected)) != len(selected):
            parser.error("Only distinct CASE-TB-001–036 IDs are permitted")
        helper = ZetarisHelperClient(args.helper)
        retrieval = lambda cid: reconcile_case(helper, namespace=args.namespace, case_id=cid)
    result = build_report(selected, retrieval)
    dest = args.output.expanduser().resolve()
    if dest.suffix.lower() != ".json":
        parser.error("--output must have .json extension")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    dest.chmod(0o600)
    print(json.dumps({
        key: result[key] for key in (
            "cases_requested", "cases_fully_readable_and_evaluated",
            "cases_with_impaired_source_access", "cases_blocked_no_evidence",
            "cases_failed_validation_or_read", "cases_evaluated_with_valid_plans",
            "total_proposed_checks_not_executed", "model_calls",
        )
    }, indent=2))
    print(f"Report written: {dest}")
    return 0 if not result["cases_failed_validation_or_read"] and not (
        result["cases_blocked_no_evidence"]
    ) and not result["cases_with_impaired_source_access"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
