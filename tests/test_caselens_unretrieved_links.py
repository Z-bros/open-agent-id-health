"""Regression: model prompt must never expose dangling IDs as retrieved citations.

The critic still rejects any unrecognized identifier from the LLM.
"""
import copy
import json
from pathlib import Path
import unittest

from apps.caselens.explain import describe_case, CaseLensValidationError

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


def unresolved_link_case():
    bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
    bundle["observations"][2]["details"]["order_id"] = "ORD-TB-999"
    bundle["exceptions"] = [{
        "category": "cross_source_link_mismatch",
        "description": (
            "lab_results.order_id does not match a returned lab_orders ID; "
            "source linkage requires verification."
        ),
        "evidence_record_ids": ["RES-TB-018"],
    }]
    return bundle


class CapturingClient:
    def __init__(self, *, invent_reference=False):
        self.messages = None
        self.invent_reference = invent_reference

    def complete(self, messages):
        self.messages = messages
        reason = (
            "The retrieved synthetic result RES-TB-018 has an order_id "
            "link field with no matching retrieved order record; "
            "the mismatch requires source verification."
        )
        if self.invent_reference:
            reason += " A supposed unreturned record ORD-TB-999 is referenced."
        return json.dumps({"explanations": [{
            "finding_index": 0,
            "reason": reason,
            "unresolved_question": (
                "Can staff compare RES-TB-018 against retrieved lab_orders "
                "without inferring the missing target?"
            ),
        }]})


class UnretrievedLinkTest(unittest.TestCase):
    def test_model_receives_field_status_not_dangling_identifier(self):
        bundle = unresolved_link_case()
        client = CapturingClient()
        report = describe_case(bundle, client)
        self.assertEqual(report["case_id"], "CASE-TB-018")
        self.assertEqual(
            report["hypotheses"][0]["hypothesis"],
            "Administrative review finding: cross_source_link_mismatch",
        )
        self.assertEqual(report["hypotheses"][0]["evidence_record_ids"],
                         ["RES-TB-018"])
        sent = client.messages[-1]["content"]
        self.assertNotIn("ORD-TB-999", sent)
        prompt = json.loads(sent.split("\n", 1)[1])
        result = next(e for e in prompt["evidence"] if e["record_id"] == "RES-TB-018")
        self.assertEqual(result["unretrieved_link_fields"], ["order_id"])
        self.assertEqual(result["retrieved_links"], {})
        self.assertIn("ORD-TB-018", prompt["allowed_retrieved_record_ids"])
        self.assertNotIn("ORD-TB-999", prompt["allowed_retrieved_record_ids"])
        self.assertTrue(report["requires_human_approval"])

    def test_validator_still_rejects_model_inventing_missing_record(self):
        client = CapturingClient(invent_reference=True)
        with self.assertRaisesRegex(CaseLensValidationError, "non-retrieved"):
            describe_case(unresolved_link_case(), client)
        self.assertNotIn("ORD-TB-999", client.messages[-1]["content"])

    def test_existing_subject_mismatch_keeps_both_synthetic_subjects(self):
        bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))
        class SubjectClient:
            def complete(self, messages):
                contents = json.loads(messages[-1]["content"].split("\n", 1)[1])
                assert contents["evidence"][2]["retrieved_links"] == {
                    "order_id": "ORD-TB-018"
                }
                return json.dumps({"explanations":[{
                    "finding_index": 0,
                    "reason": (
                        "Case CASE-TB-018 references SYN-SUBJ-018 while "
                        "result RES-TB-018 references SYN-SUBJ-999; "
                        "the administrative subject conflict needs review."
                    ),
                    "unresolved_question": (
                        "Which synthetic subject belongs to RES-TB-018 "
                        "after human source verification?"
                    ),
                }]})
        report = describe_case(bundle, SubjectClient())
        self.assertEqual(report["hypotheses"][0]["assessment"], "supported")


if __name__ == "__main__":
    unittest.main()
