"""E08: archive validated E04/E05 artifacts without pretending proposed checks occurred.

All fixtures are fabricated; no access to actual NVIDIA/Zetaris/Meterless in
these tests. Real Meterless behavior is verified in the GitHub workflow.
"""
import copy
import json
from pathlib import Path
import unittest

from apps.nextstep.plan import plan_case
from shared.meterless.adapter import world_observations, canonical_json

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


def bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def explanation():
    return {
        "schema_version": "1.0.0",
        "case_id": "CASE-TB-018",
        "hypotheses": [{
            "hypothesis": "Administrative review finding: subject_mismatch",
            "assessment": "supported",
            "reason": (
                "Synthetic registry CASE-TB-018 references SYN-SUBJ-018 but "
                "synthetic lab result RES-TB-018 references SYN-SUBJ-999; "
                "this administrative conflict needs human verification."
            ),
            "evidence_record_ids": ["CASE-TB-018", "RES-TB-018"],
        }],
        "unresolved_questions": [
            "Can a human reviewer verify the registry CASE-TB-018 and result RES-TB-018?"
        ],
        "requires_human_approval": True,
    }


class AgentAuditTests(unittest.TestCase):
    def test_legacy_e03_remains_stable(self):
        self.assertEqual(len(world_observations(bundle())), 4)

    def test_both_reports_are_ingested_as_distinct_synthetic_agent_observations(self):
        b = bundle()
        entries = world_observations(
            b, explanation=explanation(), plan=plan_case(b)
        )
        self.assertEqual(len(entries), 6)
        self.assertEqual(len({e["externalId"] for e in entries}), 6)
        exp = next(e for e in entries if e["type"] == "tb_caselens_explanation")
        nxt = next(e for e in entries if e["type"] == "tb_nextstep_plan")
        self.assertEqual(exp["externalId"],
                         "tb-careos:CASE-TB-018:caselens:explanation-report:v1")
        self.assertEqual(nxt["externalId"],
                         "tb-careos:CASE-TB-018:nextstep:verification-plan:v1")
        self.assertEqual(json.loads(exp["text"])["report"], explanation())
        archived_plan = json.loads(nxt["text"])
        self.assertEqual(archived_plan["execution_status"], "not_executed")
        self.assertTrue(archived_plan["plan"]["requires_human_approval"])
        self.assertEqual([x["action"] for x in archived_plan["plan"]["actions"][-2:]],
                         ["manual_review", "stop"])
        self.assertEqual(exp["at"], nxt["at"])
        self.assertTrue(all(e["source"]["at"] == e["at"] for e in entries))
        self.assertNotIn("ground_truth_holdout", canonical_json(entries))

    def test_no_nemotron_call_is_needed_for_persisting_saved_reports(self):
        b = bundle()
        self.assertEqual(len(world_observations(b, explanation=explanation())), 5)
        self.assertEqual(len(world_observations(b, plan=plan_case(b))), 5)

    def test_same_data_replay_is_canonical_and_stable(self):
        b = bundle()
        p = plan_case(b)
        first = world_observations(b, explanation=explanation(), plan=p)
        second = world_observations(b, explanation=explanation(), plan=p)
        self.assertEqual(canonical_json(first), canonical_json(second))
        self.assertEqual([e["externalId"] for e in first],
                         [e["externalId"] for e in second])

    def test_revised_explanation_changes_text_not_event_identity(self):
        b = bundle()
        x = explanation()
        first = next(e for e in world_observations(b, explanation=x)
                     if e["type"] == "tb_caselens_explanation")
        x = copy.deepcopy(x)
        x["hypotheses"][0]["reason"] = (
            "On this evidence snapshot, registry CASE-TB-018 names SYN-SUBJ-018 "
            "while result RES-TB-018 names SYN-SUBJ-999; staff should verify."
        )
        second = next(e for e in world_observations(b, explanation=x)
                      if e["type"] == "tb_caselens_explanation")
        self.assertEqual(first["externalId"], second["externalId"])
        self.assertNotEqual(first["text"], second["text"])

    def test_cross_case_or_fabricated_evidence_citation_is_rejected(self):
        b = bundle()
        x = explanation()
        x["case_id"] = "CASE-TB-999"
        with self.assertRaises(ValueError):
            world_observations(b, explanation=x)
        x = explanation()
        x["hypotheses"][0]["evidence_record_ids"].append("RES-TB-999")
        with self.assertRaises(ValueError):
            world_observations(b, explanation=x)

    def test_clinical_claim_or_subject_hallucination_is_rejected(self):
        b = bundle()
        x = explanation()
        x["hypotheses"][0]["reason"] = (
            "The patient missed treatment. CASE-TB-018 names SYN-SUBJ-018 "
            "and RES-TB-018 names SYN-SUBJ-999."
        )
        with self.assertRaises(ValueError):
            world_observations(b, explanation=x)
        x = explanation()
        x["hypotheses"][0]["reason"] += " SYN-SUBJ-777"
        with self.assertRaises(ValueError):
            world_observations(b, explanation=x)

    def test_plan_cannot_invent_action_or_unapproved_source(self):
        b = bundle()
        p = plan_case(b)
        p["actions"][0]["action"] = "contact_patient"
        with self.assertRaises(ValueError):
            world_observations(b, plan=p)
        p = plan_case(b)
        p["actions"][0]["source_system"] = "private_patient_registry"
        with self.assertRaises(ValueError):
            world_observations(b, plan=p)

    def test_wrong_case_plan_rejected(self):
        b = bundle()
        p = plan_case(b)
        p["case_id"] = "CASE-TB-777"
        with self.assertRaises(ValueError):
            world_observations(b, plan=p)

    def test_invalid_missing_case_validation_does_not_archive(self):
        b = bundle()
        del b["observations"][0]["details"]["case_id"]
        with self.assertRaises(ValueError):
            world_observations(b, explanation=explanation(), plan=plan_case(bundle()))


if __name__ == "__main__":
    unittest.main()
