"""Offline test harness for E10; fake transport, real grounded validators."""
import json
from pathlib import Path
import unittest

from apps.evaluation.nemotron_reliability import evaluate_live, DEFAULT_CASES, _error_category
from apps.careflow.tb_zetaris_probe import EVIDENCE_SOURCES
from shared.inference.nemotron import NemotronError

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


def source_bundle(cid="CASE-TB-018", normal=False):
    b = json.loads(FIXTURE.read_text().replace("018", cid[-3:]))
    b["source_checks"] = [
        {"source_system": name, "attempt": 1,
         "status": "available" if name in {"cases", "lab_orders", "lab_results"} else "not_found"}
        for name in EVIDENCE_SOURCES
    ]
    if normal:
        b["exceptions"] = []
    return b


class Provider:
    def __init__(self, mode="success"):
        self.mode = mode

    def complete(self, messages):
        if self.mode == "failed":
            raise NemotronError("NVIDIA API HTTP 403; private token secret-123")
        payload = json.loads(messages[-1]["content"].split("\n", 1)[1])
        if "allowed_queries" in payload:
            return json.dumps({"selected_query_ids":
                ["q999"] if self.mode == "bad_plan" else [payload["allowed_queries"][0]["query_id"]]})
        sources = {x["record_id"]: x for x in payload["evidence"]}
        explanations = []
        for finding in payload["careflow_findings"]:
            refs = finding["evidence_record_ids"]
            reason = ("Fabricated evidence " + ", ".join(refs) +
                      " warrants administrative review, with no inference about care.")
            if finding["category"] == "subject_mismatch":
                subjects = sorted({sources[ref]["subject_ref"] for ref in refs})
                reason += " Synthetic subjects differ: " + " and ".join(subjects) + "."
            explanations.append({
                "finding_index": finding["finding_index"],
                "reason": reason,
                "unresolved_question": "Which synthetic record should staff verify first?",
            })
        return json.dumps({"explanations": explanations})


class Tests(unittest.TestCase):
    def test_accepted_provider_and_no_call_baseline_separate(self):
        out = evaluate_live(
            ["CASE-TB-001", "CASE-TB-018"],
            lambda cid: source_bundle(cid, normal=cid == "CASE-TB-001"),
            lambda: Provider())
        self.assertEqual(out["cases_with_verified_sources"], 2)
        self.assertEqual(out["model_calls"], 2)
        self.assertEqual(out["provider_accepted"], 2)
        self.assertEqual(out["no_provider_needed"], 2)
        self.assertEqual(out["rejected_or_failed"], 0)
        self.assertEqual(out["full_chain_eligible_trials"], 1)
        self.assertEqual(out["full_chain_accepted"], 1)
        self.assertEqual(out["agents"]["CaseLens"]["model_calls"], 1)
        self.assertEqual(out["agents"]["NextStep"]["model_calls"], 1)
        self.assertEqual(out["proposed_queries_executed"], 0)
        self.assertFalse(out["ground_truth_holdout_used"])
        self.assertNotIn("Synthetic subjects differ", json.dumps(out))

    def test_repeats_frozen_source_and_explicit_call_count(self):
        received = []
        def retrieval(cid):
            received.append(cid)
            return source_bundle(cid)
        out = evaluate_live(["CASE-TB-018"], retrieval, lambda: Provider(), repeats=2)
        self.assertEqual(received, ["CASE-TB-018"])
        self.assertEqual(out["model_calls"], 4)
        self.assertEqual(out["provider_accepted"], 4)
        self.assertEqual(len(out["results"][0]["trials"]), 2)

    def test_provider_errors_fail_closed_and_no_secrets_leak(self):
        out = evaluate_live(["CASE-TB-018"], lambda _: source_bundle(), lambda: Provider("failed"))
        self.assertEqual(out["model_calls"], 2)
        self.assertEqual(out["rejected_or_failed"], 2)
        self.assertEqual(out["full_chain_eligible_trials"], 1)
        self.assertEqual(out["full_chain_accepted"], 0)
        self.assertEqual(out["agents"]["CaseLens"]["failure_categories"], {"provider_http_403": 1})
        self.assertEqual(out["agents"]["NextStep"]["failure_categories"], {"provider_http_403": 1})
        self.assertNotIn("secret-123", json.dumps(out))

    def test_critic_failure_is_not_offline_fallback(self):
        attempts = iter([Provider(), Provider("bad_plan")])
        out = evaluate_live(["CASE-TB-018"], lambda _: source_bundle(), lambda: next(attempts))
        self.assertEqual(out["provider_accepted"], 1)
        self.assertEqual(out["rejected_or_failed"], 1)
        self.assertEqual(out["agents"]["NextStep"]["failure_categories"],
                         {"nextstep_non_allowlisted_query": 1})

    def test_source_error_is_counted_before_provider(self):
        factory_calls = []
        def retrieval(cid):
            if cid == "CASE-TB-009":
                raise RuntimeError("secret-123")
            return source_bundle(cid)
        def factory():
            factory_calls.append(True)
            return Provider()
        out = evaluate_live(["CASE-TB-009", "CASE-TB-018"], retrieval, factory)
        self.assertEqual(out["cases_without_verified_sources"], 1)
        self.assertEqual(out["model_calls"], 2)
        self.assertEqual(len(factory_calls), 2)
        self.assertNotIn("secret-123", json.dumps(out))

    def test_rejects_unknown_or_duplicate_or_oversized(self):
        for cases, repeats in [
            (["CASE-TB-999"], 1),
            (["CASE-TB-018", "CASE-TB-018"], 1),
            (["CASE-TB-018"], 3),
            (list(DEFAULT_CASES) * 3, 1),
        ]:
            with self.subTest(cases=cases, repeats=repeats), self.assertRaises(ValueError):
                evaluate_live(cases, lambda cid: source_bundle(cid), lambda: Provider(),
                              repeats=repeats)

    def test_specific_caselens_rejection_categories_do_not_leak_text(self):
        from apps.caselens.explain import CaseLensValidationError
        from apps.nextstep.plan import NextStepValidationError
        from apps.evaluation.nemotron_reliability import _error_category
        samples = [
            ("Model reason omitted mandatory source business ID", "caselens_missing_business_citation"),
            ("Nemotron cited a non-retrieved event or source record", "caselens_unretrieved_citation"),
            ("Nemotron did not return strict JSON", "caselens_invalid_json"),
        ]
        for safe_message, expected in samples:
            self.assertEqual(_error_category(CaseLensValidationError(safe_message)), expected)
        self.assertEqual(
            _error_category(CaseLensValidationError("Private provider text sk-secret")),
            "caselens_other_contract_rejection",
        )
        self.assertEqual(
            _error_category(NextStepValidationError("Nemotron selected a non-allowlisted query")),
            "nextstep_non_allowlisted_query",
        )

    def test_safe_error_categories(self):
        self.assertEqual(_error_category(NemotronError("NVIDIA API HTTP 429; secret")),
                         "provider_http_429")
        self.assertEqual(_error_category(NemotronError("NVIDIA request timed out")),
                         "provider_timeout")


if __name__ == "__main__":
    unittest.main()
