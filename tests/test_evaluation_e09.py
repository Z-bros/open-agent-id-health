"""E09 offline contract evaluation tests. Mirrored fixture is NOT accuracy ground truth."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.evaluation.__main__ import build_report, evaluate_bundle, main, CASE_IDS
from apps.careflow.tb_zetaris_probe import EVIDENCE_SOURCES

ROOT = Path(__file__).resolve().parent
FIXTURE = ROOT / "fixtures/tb_case_018_bundle.json"


def case_bundle(cid="CASE-TB-018"):
    b = json.loads(FIXTURE.read_text(encoding="utf-8"))
    # This is a unit-test-only simulated fixture; not 36 independently
    # labelled real scenarios, and never a measured detection rate.
    serialized = json.dumps(b).replace("018", cid[-3:])
    b = json.loads(serialized)
    b["source_checks"] = [
        {"source_system": table, "attempt": 1,
         "status": "available" if table in {
             "cases", "lab_orders", "lab_results"
         } else "not_found"} for table in EVIDENCE_SOURCES
    ]
    return b


class EvaluationTests(unittest.TestCase):
    def test_one_cited_subject_mismatch_evaluates_without_model(self):
        b = case_bundle()
        record = evaluate_bundle(b, "CASE-TB-018")
        self.assertEqual(record["status"], "evaluated")
        self.assertEqual(record["observation_count"], 3)
        self.assertEqual(record["findings_by_category"], {"subject_mismatch": 1})
        self.assertEqual(record["plan_query_count"], 2)
        self.assertTrue(record["citation_integrity"])
        self.assertEqual(record["missing_evidence_interpretation"], "unverified")
        self.assertFalse(record["heldout_labels_used"])

    def test_all_36_simulated_case_ids_are_counted_not_claimed_accuracy(self):
        report = build_report(list(CASE_IDS), lambda cid: case_bundle(cid))
        self.assertEqual(report["cases_requested"], 36)
        self.assertEqual(report["cases_accounted_for"], 36)
        self.assertEqual(report["cases_evaluated_with_valid_plans"], 36)
        self.assertEqual(report["cases_fully_readable_and_evaluated"], 36)
        self.assertEqual(report["findings_by_category"]["subject_mismatch"], 36)
        self.assertEqual(report["total_proposed_checks_not_executed"], 72)
        self.assertEqual(report["model_calls"], 0)
        self.assertFalse(report["ground_truth_holdout_used"])
        self.assertTrue(any("No exception detection accuracy" in l
                            for l in report["limitations"]))
        self.assertEqual(len(report["case_results"]), 36)

    def test_rejects_wrong_case_and_dangling_citations(self):
        b = case_bundle()
        with self.assertRaisesRegex(ValueError, "cross-case"):
            evaluate_bundle(b, "CASE-TB-009")
        b["exceptions"][0]["evidence_record_ids"] = ["RES-TB-999"]
        with self.assertRaisesRegex(ValueError, "unretrieved"):
            evaluate_bundle(b, "CASE-TB-018")

    def test_source_unavailability_is_not_claimed_clean(self):
        b = case_bundle()
        for check in b["source_checks"]:
            if check["source_system"] == "lab_results":
                check["status"] = "permission_denied"
        report = build_report(["CASE-TB-018"], lambda _: b)
        self.assertEqual(report["cases_fully_readable_and_evaluated"], 0)
        self.assertEqual(report["cases_with_impaired_source_access"], 1)
        self.assertEqual(report["cases_evaluated_with_valid_plans"], 1)
        self.assertEqual(report["case_results"][0]["inaccessible_sources"],
                         ["lab_results"])

    def test_empty_sources_are_blocked_not_passed(self):
        b = case_bundle()
        b["observations"] = []
        b["exceptions"] = []
        b["source_checks"] = [
            {"source_system": table, "attempt": 1, "status": "not_found"}
            for table in EVIDENCE_SOURCES
        ]
        report = build_report(["CASE-TB-018"], lambda _: b)
        self.assertEqual(report["cases_blocked_no_evidence"], 1)
        self.assertEqual(report["cases_evaluated_with_valid_plans"], 0)

    def test_failed_retrieval_never_disappears_or_leaks_sensitive_details(self):
        def unavailable(_cid):
            raise RuntimeError("private token sk-test-sensitive")
        report = build_report(["CASE-TB-018", "CASE-TB-009"], unavailable)
        self.assertEqual(report["cases_requested"], 2)
        self.assertEqual(report["cases_failed_validation_or_read"], 2)
        self.assertNotIn("sk-test-sensitive", json.dumps(report))
        self.assertTrue(all(x["failure_category"] == "RuntimeError"
                            for x in report["case_results"]))

    def test_rejects_duplicate_unknown_case_and_source_mismatch(self):
        with self.assertRaises(ValueError):
            build_report(["CASE-TB-018"] * 2, lambda cid: case_bundle(cid))
        with self.assertRaises(ValueError):
            build_report(["CASE-TB-999"], lambda cid: case_bundle(cid))
        b = case_bundle()
        b["source_checks"].pop()
        with self.assertRaisesRegex(ValueError, "Five expected"):
            evaluate_bundle(b, "CASE-TB-018")

    def test_clinical_claim_in_rule_description_fails_closed(self):
        b = case_bundle()
        b["exceptions"][0]["description"] = "The patient missed treatment."
        with self.assertRaisesRegex(ValueError, "clinical language"):
            evaluate_bundle(b, "CASE-TB-018")

    def test_offline_fixture_cli_needs_no_provider_or_holdout(self):
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "evaluation.json"
            from contextlib import redirect_stdout
            from io import StringIO
            with redirect_stdout(StringIO()):
                result = main([
                    "--bundle", str(FIXTURE),
                    "--output", str(output),
                ])
            # The saved E04 fixture has only three source checks, not a
            # full E02 live five-table read: fail honestly, keep report.
            self.assertEqual(result, 2)
            info = json.loads(output.read_text())
            self.assertEqual(info["cases_requested"], 1)
            self.assertEqual(info["cases_failed_validation_or_read"], 1)
            self.assertFalse(info["ground_truth_holdout_used"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
