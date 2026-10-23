"""E10: small, rate-bounded *live* Nemotron reliability study on synthetic cases.

Unlike E09 this invokes the provider. It records only accepted/rejected
contract outcomes and safe failure categories, not raw provider text.
It does not query or read any holdout, execute plans or write to Zetaris.
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
from time import perf_counter
from typing import Any, Callable

from apps.caselens.explain import CaseLensValidationError, describe_case
from apps.evaluation.__main__ import CASE_IDS, evaluate_bundle
from apps.careflow.reconcile import reconcile_case
from apps.nextstep.plan import NextStepValidationError, plan_case, validate_plan
from shared.inference.nemotron import NVIDIAChatClient, NemotronError, LIGHTNING_MODEL
from shared.zetaris.readonly import ZetarisHelperClient

# One normal case and one representative case from each of the five
# known administrative finding categories, according to E09's actual run.
DEFAULT_CASES = (
    "CASE-TB-001",  # normal source snapshot, no CareFlow findings
    "CASE-TB-002",  # duplicate_business_event_replay
    "CASE-TB-004",  # followup_document_not_found_in_query
    "CASE-TB-007",  # cross_source_link_mismatch
    "CASE-TB-009",  # lab_document_not_found_in_query
    "CASE-TB-018",  # subject_mismatch
)
MAX_PROVIDER_CALLS = 30
ERROR_HTTP = re.compile(r"NVIDIA API HTTP (\d{3})")


# Exact messages authored by our own validators, never raw model text.
CASELENS_RULES = {
    "Nemotron did not return strict JSON": "caselens_invalid_json",
    "Nemotron returned an invalid top-level structure": "caselens_structure",
    "Nemotron must address every CareFlow finding exactly once": "caselens_finding_coverage",
    "Model fields not allowlisted": "caselens_fields",
    "Model finding index invalid/duplicate": "caselens_index",
    "Model reason unsafe or out of bounds": "caselens_reason_safety_or_length",
    "Model review question unsafe or missing question mark": "caselens_question_format",
    "Nemotron cited a non-retrieved event or source record": "caselens_unretrieved_citation",
    "Nemotron introduced an unknown subject identifier": "caselens_unknown_subject",
    "Explanation contains an unsupported external reference": "caselens_external_reference",
    "Model reason omitted mandatory source business ID": "caselens_missing_business_citation",
    "Subject mismatch reason lacks both conflicting subjects": "caselens_missing_subject_refs"
}
NEXTSTEP_RULES = {
    "Nemotron selection was not strict JSON": "nextstep_invalid_json",
    "Nemotron tried to output unsupported plan fields": "nextstep_fields",
    "Nemotron query selection violates bounds": "nextstep_selection_bounds",
    "Nemotron selected a non-allowlisted query": "nextstep_non_allowlisted_query"
}


class CountingClient:
    def __init__(self, delegate: Any):
        self.delegate = delegate
        self.calls = 0

    def complete(self, messages: list[dict[str, str]]) -> str:
        self.calls += 1
        return self.delegate.complete(messages)


def _error_category(exc: Exception) -> str:
    """No raw model answer, payload, or underlying exception is persisted."""
    if isinstance(exc, NemotronError):
        match = ERROR_HTTP.search(str(exc))
        if match:
            return "provider_http_" + match.group(1)
        message = str(exc)
        if "API_KEY not set" in message:
            return "provider_key_missing"
        if "timed out" in message:
            return "provider_timeout"
        if "connection failed" in message:
            return "provider_connection_error"
        return "provider_incomplete_or_other"
    if isinstance(exc, CaseLensValidationError):
        return CASELENS_RULES.get(str(exc), "caselens_other_contract_rejection")
    if isinstance(exc, NextStepValidationError):
        return NEXTSTEP_RULES.get(str(exc), "nextstep_other_contract_rejection")
    return "unexpected_" + type(exc).__name__


def _measure(agent_name: str, operation: Callable[[], dict], client: CountingClient,
             *, expected_case_id: str) -> tuple[dict, dict | None]:
    start = perf_counter()
    report = None
    try:
        report = operation()
        if report["case_id"] != expected_case_id or report["requires_human_approval"] is not True:
            raise ValueError("Wrong case ID or approval flag")
        status = "accepted_provider" if client.calls > 0 else "no_provider_needed"
        error = None
    except Exception as exc:
        status = "rejected_or_failed"
        error = _error_category(exc)
        report = None
    duration_ms = max(0, round((perf_counter() - start) * 1000))
    return ({
        "agent": agent_name,
        "status": status,
        "provider_calls": client.calls,
        "duration_ms": duration_ms,
        "error_category": error,
    }, report)


def evaluate_live(
    cases: list[str], retrieve: Callable[[str], dict],
    client_factory: Callable[[], Any], *, repeats: int = 1,
) -> dict:
    """Read each source case exactly once; repeat inference on frozen evidence."""
    if (not isinstance(cases, list) or not cases or len(cases) > 15 or
        len(set(cases)) != len(cases) or any(cid not in CASE_IDS for cid in cases) or
        type(repeats) is not int or not 1 <= repeats <= 2 or
        2 * repeats * len(cases) > MAX_PROVIDER_CALLS):
        raise ValueError("E10 accepts ≤15 distinct synthetic cases, 1–2 runs, ≤30 potential provider calls")
    rows = []
    for case_id in cases:
        try:
            bundle = retrieve(case_id)
            # E09 verifies five-source provenance, contract, citations and
            # deterministic plan safety; no model calls occur in this step.
            verified = evaluate_bundle(bundle, case_id)
            if verified["status"] != "evaluated":
                raise ValueError("Source evidence not fully accessible/validated")
        except Exception as exc:
            rows.append({
                "case_id": case_id, "status": "source_not_evaluable",
                "source_error_category": _error_category(exc),
                "findings": [],
                "trials": [],
            })
            continue

        result = {
            "case_id": case_id,
            "status": "evaluated",
            "findings": [f["category"] for f in bundle["exceptions"]],
            "observations": len(bundle["observations"]),
            "trials": [],
        }
        for trial_num in range(1, repeats + 1):
            try:
                first = CountingClient(client_factory())
                exp_metric, explanation = _measure(
                    "CaseLens", lambda: describe_case(bundle, first),
                    first, expected_case_id=case_id,
                )
            except Exception as exc:
                explanation = None
                exp_metric = {
                    "agent": "CaseLens", "status": "rejected_or_failed",
                    "provider_calls": 0, "duration_ms": 0,
                    "error_category": _error_category(exc),
                }

            try:
                second = CountingClient(client_factory())
                def make_plan() -> dict:
                    plan = plan_case(bundle, model_client=second, explanation=explanation)
                    validate_plan(bundle, plan)
                    return plan
                plan_metric, verified_plan = _measure(
                    "NextStep", make_plan, second, expected_case_id=case_id,
                )
            except Exception as exc:
                verified_plan = None
                plan_metric = {
                    "agent": "NextStep", "status": "rejected_or_failed",
                    "provider_calls": 0, "duration_ms": 0,
                    "error_category": _error_category(exc),
                }
            plan_queries = (
                sum(a["action"] == "read_only_source_query"
                    for a in verified_plan["actions"])
                if verified_plan is not None else None
            )
            result["trials"].append({
                "trial": trial_num,
                "caselens": exp_metric,
                "nextstep": plan_metric,
                "case_lens_linked_to_nextstep": explanation is not None,
                "nextstep_proposed_checks_not_executed": plan_queries,
                "human_approval_preserved": bool(
                    (explanation is None or explanation["requires_human_approval"]) and
                    (verified_plan is None or verified_plan["requires_human_approval"])
                ),
                "source_mutations": 0,
                "proposed_actions_executed": 0,
            })
        rows.append(result)

    # Report linked success, not just independent successful agent calls.
    eligible_chains = [t for c in rows if c.get("findings") for t in c["trials"]]
    linked_chains = sum(
        t["caselens"]["status"] == "accepted_provider" and
        t["nextstep"]["status"] in ("accepted_provider", "no_provider_needed")
        for t in eligible_chains
    )
    calls = 0
    successes = 0
    failures = 0
    no_need = 0
    by_agent: dict[str, dict] = {}
    for name, field in (("CaseLens", "caselens"), ("NextStep", "nextstep")):
        items = [trial[field] for case in rows for trial in case["trials"]]
        accepted = sum(item["status"] == "accepted_provider" for item in items)
        no_provider = sum(item["status"] == "no_provider_needed" for item in items)
        failed = sum(item["status"] == "rejected_or_failed" for item in items)
        n_calls = sum(item["provider_calls"] for item in items)
        calls += n_calls
        successes += accepted
        failures += failed
        no_need += no_provider
        by_agent[name] = {
            "model_calls": n_calls,
            "provider_accepted": accepted,
            "no_provider_needed": no_provider,
            "rejected_or_failed": failed,
            "accepted_among_actual_provider_calls": (
                round(accepted / n_calls, 4) if n_calls else None
            ),
            "failure_categories": dict(sorted(Counter(
                item["error_category"] for item in items if item["error_category"]
            ).items())),
        }

    return {
        "schema_version": "1.0.0",
        "evaluation_type": "hosted_nemotron_bounded_contract_acceptance",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": LIGHTNING_MODEL,  # set by live CLI; tests use the same identifier
        "cases_requested": len(cases),
        "cases_with_verified_sources": sum(c["status"] == "evaluated" for c in rows),
        "cases_without_verified_sources": sum(c["status"] != "evaluated" for c in rows),
        "repeats_per_case": repeats,
        "model_calls": calls,
        "provider_accepted": successes,
        "full_chain_eligible_trials": len(eligible_chains),
        "full_chain_accepted": linked_chains,
        "no_provider_needed": no_need,
        "rejected_or_failed": failures,
        "agents": by_agent,
        "source_mutations": 0,
        "proposed_queries_executed": 0,
        "ground_truth_holdout_used": False,
        "cautions": [
            "Provider acceptance is contract/grounding validator success, not independently human-graded factual accuracy.",
            "A zero-finding case may invoke no LLM; no-provider-needed is excluded from model reliability denominator.",
            "Failures include provider availability, timeouts and strict output rejection; no silent offline fallback.",
            "The evidence snapshot is read once per case for comparable repeats; no proposed checks are executed.",
            "No clinical accuracy, population performance, recall, or hallucination-free certification is claimed.",
        ],
        "results": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-ids", nargs="+", default=list(DEFAULT_CASES))
    parser.add_argument("--repeats", type=int, default=1, choices=(1, 2))
    parser.add_argument("--namespace", default="TBCARE_OS")
    parser.add_argument("--helper", default=os.getenv("TB_CAREOS_ZETARIS_QUERY_HELPER"))
    parser.add_argument("--model", default=LIGHTNING_MODEL)
    parser.add_argument("--output", type=Path, default=Path("outputs/e10_nemotron_reliability.json"))
    args = parser.parse_args(argv)
    if not args.helper:
        parser.error("--helper must point to the trusted official Zetaris query helper")
    if not os.getenv("NVIDIA_API_KEY"):
        parser.error("NVIDIA_API_KEY missing in this WSL shell; load it privately (never print it)")
    if len(args.case_ids) * args.repeats * 2 > MAX_PROVIDER_CALLS:
        parser.error("Potential model calls exceed 30; reduce --case-ids or --repeats")
    client = ZetarisHelperClient(args.helper)
    report = evaluate_live(
        args.case_ids,
        lambda cid: reconcile_case(client, namespace=args.namespace, case_id=cid),
        lambda: NVIDIAChatClient(model=args.model),
        repeats=args.repeats,
    )
    report["model"] = args.model
    output = args.output.expanduser().resolve()
    if output.suffix.lower() != ".json":
        parser.error("--output must end in .json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    output.chmod(0o600)
    summary = {key: report[key] for key in (
        "cases_requested", "cases_with_verified_sources",
        "cases_without_verified_sources", "repeats_per_case",
        "model_calls", "provider_accepted", "full_chain_eligible_trials",
        "full_chain_accepted", "no_provider_needed",
        "rejected_or_failed", "agents",
    )}
    print(json.dumps(summary, indent=2))
    print("Saved synthetic model evaluation report:", output)
    return 0 if report["rejected_or_failed"] == 0 and report["cases_without_verified_sources"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
