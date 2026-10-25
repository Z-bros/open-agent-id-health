"""E05 offline NextStep tests: no provider calls, source writes or holdouts."""
import copy
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import json
from pathlib import Path
import unittest

from apps.nextstep.__main__ import main
from apps.nextstep.plan import NextStepValidationError, plan_case, validate_plan

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/tb_case_018_bundle.json"


class Model:
    def __init__(self, selected):
        self.selected = selected
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return self.selected


def fixture():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class NextStepTests(unittest.TestCase):
    def test_offline_subject_mismatch_proposes_bounded_queries_then_stop(self):
        bundle = fixture()
        result = plan_case(bundle)
        self.assertEqual(result["case_id"], "CASE-TB-018")
        self.assertTrue(result["requires_human_approval"])
        self.assertEqual(result["schema_version"], "1.0.0")
        self.assertEqual(result["max_queries"], 3)
        self.assertEqual(
            [a["action"] for a in result["actions"]],
            ["read_only_source_query", "read_only_source_query", "manual_review", "stop"],
        )
        self.assertEqual(
            [a["source_system"] for a in result["actions"][:2]],
            ["cases", "lab_results"],
        )
        self.assertEqual(set(result["actions"][0]["evidence_record_ids"]),
                         {"CASE-TB-018", "RES-TB-018"})
        self.assertNotIn("source_system", result["actions"][-1])
        validate_plan(bundle, result)

    def test_model_can_only_select_allowed_query_ids(self):
        model = Model('{"selected_query_ids":["q2"]}')
        bundle = fixture()
        result = plan_case(bundle, model_client=model)
        self.assertEqual(len(model.calls), 1)
        self.assertEqual(model.calls[0][0]["role"], "system")
        self.assertEqual(model.calls[0][1]["role"], "user")
        self.assertIn("q2", model.calls[0][1]["content"])
        self.assertNotIn("ground_truth_holdout", json.dumps(model.calls))
        self.assertEqual(
            [a["action"] for a in result["actions"]],
            ["read_only_source_query", "manual_review", "stop"],
        )
        self.assertEqual(result["actions"][0]["source_system"], "lab_results")
        self.assertEqual(result["actions"][-2]["evidence_record_ids"],
                         ["CASE-TB-018", "RES-TB-018"])

    def test_model_cannot_invent_source_or_actions(self):
        for raw in [
            '{"selected_query_ids":["q9"]}',
            '{"selected_query_ids":["q1","q1"]}',
            '{"selected_query_ids":[]}',
            '{"selected_query_ids":["q1"],"sql":"DELETE FROM cases"}',
            '{"actions":[{"action":"contact_patient"}]}',
            '{"selected_query_ids":["q1","q2","q3"]}',
            "Sorry, I refuse",
        ]:
            with self.subTest(raw=raw), self.assertRaises(NextStepValidationError):
                plan_case(fixture(), model_client=Model(raw))

    def test_missing_documentation_is_not_a_missed_care_claim(self):
        b = fixture()
        b["observations"] = [
            obs for obs in b["observations"] if obs["record_type"] != "lab_results"
        ]
        b["exceptions"] = [{
            "category": "lab_document_not_found_in_query",
            "description": "Document was not returned in this bounded query",
            "evidence_record_ids": ["ORD-TB-018"],
        }]
        for status in b["source_checks"]:
            if status["source_system"] == "lab_results":
                status["status"] = "not_found"
        result = plan_case(b)
        self.assertEqual(result["actions"][0]["source_system"], "lab_results")
        self.assertEqual(result["actions"][0]["evidence_record_ids"], ["ORD-TB-018"])
        self.assertIn("unverified", result["actions"][0]["reason"])
        self.assertIn("human reviewer", result["actions"][-2]["reason"])
        self.assertNotIn("missed care", json.dumps(result).lower())

    def test_unavailable_source_gets_no_query_or_auto_retry(self):
        b = fixture()
        b["exceptions"] = [{
            "category": "source_query_unavailable",
            "description": "Simulated permission-denied",
            "evidence_record_ids": [],
        }]
        for check in b["source_checks"]:
            if check["source_system"] == "lab_results":
                check["status"] = "permission_denied"
        model = Model('{"selected_query_ids":["q1"]}')
        result = plan_case(b, model_client=model)
        self.assertEqual(model.calls, [])
        self.assertEqual([x["action"] for x in result["actions"]],
                         ["manual_review", "stop"])

    def test_no_findings_does_not_claim_complete_care(self):
        b = fixture()
        b["exceptions"] = []
        model = Model('{"selected_query_ids":["q1"]}')
        result = plan_case(b, model_client=model)
        self.assertEqual(model.calls, [])
        self.assertEqual([x["action"] for x in result["actions"]],
                         ["manual_review", "stop"])
        self.assertIn("may be incomplete", result["actions"][0]["reason"])

    def test_rejects_cross_case_or_non_synthetic_data(self):
        b = fixture()
        b["observations"][0]["details"]["case_id"] = "CASE-TB-777"
        with self.assertRaises(NextStepValidationError):
            plan_case(b)
        b = fixture()
        b["observations"][0]["subject_ref"] = "PRIVATE-PATIENT-123"
        with self.assertRaises(NextStepValidationError):
            plan_case(b)

    def test_critic_rejects_unapproved_source_and_extra_action(self):
        b = fixture()
        p = plan_case(b)
        altered = copy.deepcopy(p)
        altered["actions"][0]["source_system"] = "ground_truth_holdout"
        with self.assertRaises(NextStepValidationError):
            validate_plan(b, altered)
        altered = copy.deepcopy(p)
        altered["actions"][0]["action"] = "contact_patient"
        with self.assertRaises(NextStepValidationError):
            validate_plan(b, altered)
        altered = copy.deepcopy(p)
        altered["actions"].pop()
        with self.assertRaises(NextStepValidationError):
            validate_plan(b, altered)
        altered = copy.deepcopy(p)
        altered["actions"][0] = None
        with self.assertRaises(NextStepValidationError):
            validate_plan(b, altered)

    def test_explanation_cannot_add_findings_or_new_citations(self):
        b = fixture()
        legitimate = {
            "schema_version": "1.0.0",
            "case_id": b["case_id"],
            "hypotheses": [{
                "hypothesis": "Administrative review finding: subject_mismatch",
                "assessment": "supported",
                "reason": "The synthetic subject IDs differ.",
                "evidence_record_ids": ["CASE-TB-018", "RES-TB-018"],
            }],
            "unresolved_questions": ["Which source should the human reviewer verify?"],
            "requires_human_approval": True,
        }
        plan_case(b, explanation=legitimate)
        illegitimate = copy.deepcopy(legitimate)
        illegitimate["hypotheses"][0]["evidence_record_ids"].append("RES-TB-999")
        with self.assertRaises(NextStepValidationError):
            plan_case(b, explanation=illegitimate)
        illegitimate = copy.deepcopy(legitimate)
        illegitimate["case_id"] = "CASE-TB-999"
        with self.assertRaises(NextStepValidationError):
            plan_case(b, explanation=illegitimate)

    def test_contract_shape_and_action_count(self):
        b = fixture()
        contract = json.loads(
            (ROOT / "shared/contracts/verification_plan.v1.schema.json").read_text()
        )
        result = plan_case(b, max_queries=4)
        self.assertEqual(set(result), set(contract["properties"]))
        self.assertTrue(set(contract["required"]) <= set(result))
        self.assertLessEqual(len(result["actions"]),
                             contract["properties"]["actions"]["maxItems"])
        valid = contract["properties"]["actions"]["items"]["properties"]["action"]["enum"]
        for action in result["actions"]:
            self.assertIn(action["action"], valid)
            self.assertTrue(set(action) <= set(
                contract["properties"]["actions"]["items"]["properties"]))
        with self.assertRaises(NextStepValidationError):
            plan_case(b, max_queries=5)

    def test_cli_offline_with_fixture_and_no_key(self):
        stdout, stderr = StringIO(), StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = main([
                "--case-id", "CASE-TB-018",
                "--bundle", str(FIXTURE),
                "--offline",
            ])
        self.assertEqual(code, 0, stderr.getvalue())
        result = json.loads(stdout.getvalue())
        self.assertTrue(result["requires_human_approval"])

    def test_cli_rejects_case_id_mismatch(self):
        stderr = StringIO()
        with redirect_stderr(stderr), redirect_stdout(StringIO()):
            code = main([
                "--case-id", "CASE-TB-001",
                "--bundle", str(FIXTURE), "--offline",
            ])
        self.assertEqual(code, 2)
        self.assertIn("failed closed", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
