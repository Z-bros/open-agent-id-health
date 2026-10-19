import unittest
from pathlib import Path
from healthagent.synthetic import SyntheticRepository
from healthagent.workflow import Investigator

DATA = Path(__file__).resolve().parents[1] / "data" / "synthetic" / "records.json"

class WorkflowTests(unittest.TestCase):
    def run_case(self, case_id):
        repo = SyntheticRepository(DATA)
        return repo, Investigator(repo).run(repo.cases[case_id])

    def test_consistent_records_ready_for_human_review(self):
        _, pkg = self.run_case("CASE-REF-OK")
        self.assertEqual(pkg.status, "ready_for_review")
        self.assertEqual(pkg.findings, [])
        self.assertTrue(pkg.requires_human_approval)
        self.assertEqual(len(pkg.evidence), 3)

    def test_missing_record_is_not_silently_accepted(self):
        _, pkg = self.run_case("CASE-DX-MISSING")
        self.assertEqual(pkg.status, "needs_human_review")
        self.assertEqual(pkg.findings[0].kind, "missing_evidence")
        self.assertEqual(pkg.findings[0].source, "report_acknowledgement")

    def test_subject_mismatch_is_flagged_not_interpreted_clinically(self):
        _, pkg = self.run_case("CASE-TB-CONFLICT")
        self.assertEqual(pkg.status, "needs_human_review")
        self.assertEqual(pkg.findings[0].kind, "subject_mismatch")

    def test_transient_failure_recovers_with_bounded_retry(self):
        repo, pkg = self.run_case("CASE-REF-TRANSIENT")
        self.assertEqual(pkg.status, "ready_for_review")
        self.assertEqual(repo.calls[("CASE-REF-TRANSIENT", "facility_directory")], 2)
        self.assertTrue(any(s["step"] == "retry" for s in pkg.trace))

    def test_invalid_retry_budget_rejected(self):
        with self.assertRaises(ValueError):
            Investigator(SyntheticRepository(DATA), max_attempts=0)

if __name__ == "__main__":
    unittest.main()
