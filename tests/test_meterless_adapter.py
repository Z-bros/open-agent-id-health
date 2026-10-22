"""E03 unit tests: E02 -> Meterless observation conversion and isolation."""
import json
from pathlib import Path
import unittest

from shared.meterless.adapter import canonical_json, world_observations

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


class MeterlessAdapterTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_source_identity_and_citations_preserved(self):
        obs = world_observations(self.bundle)
        self.assertEqual(len(obs), 4)
        source = next(x for x in obs if ":source:lab_results:" in x["externalId"])
        self.assertEqual(source["externalId"],
                         "tb-careos:CASE-TB-018:source:lab_results:LAB_SIM:ROW-RES-018-A")
        body = json.loads(source["text"])
        self.assertEqual(body["business_event_id"], "RES-TB-018")
        self.assertEqual(body["source_record_id"], "ROW-RES-018-A")
        self.assertEqual(body["subject_ref"], "SYN-SUBJ-999")
        self.assertTrue(all(x["source"]["at"] == x["at"] for x in obs))
        finding = next(x for x in obs if ":finding:" in x["externalId"])
        summary = json.loads(finding["text"])
        self.assertEqual(summary["evidence_record_ids"], ["CASE-TB-018", "RES-TB-018"])
        self.assertTrue(summary["requires_human_approval"])

    def test_conversion_is_stable_under_reordered_input(self):
        first = world_observations(self.bundle)
        self.bundle["observations"].reverse()
        self.bundle["exceptions"].reverse()
        second = world_observations(self.bundle)
        self.assertEqual(canonical_json(first), canonical_json(second))

    def test_distinct_ingest_row_provenance_not_collapsed(self):
        imported = dict(self.bundle["observations"][-1])
        imported["source_record_id"] = "ROW-RES-018-B"
        self.bundle["observations"].append(imported)
        entries = world_observations(self.bundle)
        ids = [x["externalId"] for x in entries if ":source:lab_results:" in x["externalId"]]
        self.assertEqual(len(ids), 2)
        self.assertNotEqual(*ids)

    def test_edited_exception_description_updates_same_external_id(self):
        first = next(x for x in world_observations(self.bundle) if ":finding:" in x["externalId"])
        self.bundle["exceptions"][0]["description"] = "Revised synthetic administrative review note."
        second = next(x for x in world_observations(self.bundle) if ":finding:" in x["externalId"])
        self.assertEqual(first["externalId"], second["externalId"])
        self.assertNotEqual(first["text"], second["text"])

    def test_rejects_real_or_cross_case_subject(self):
        self.bundle["observations"][-1]["subject_ref"] = "REAL-12345"
        with self.assertRaises(ValueError):
            world_observations(self.bundle)
        self.bundle["observations"][-1]["subject_ref"] = "SYN-SUBJ-999"
        self.bundle["observations"][-1]["details"]["case_id"] = "CASE-TB-099"
        with self.assertRaises(ValueError):
            world_observations(self.bundle)

    def test_rejects_missing_source_citation(self):
        self.bundle["exceptions"][0]["evidence_record_ids"].append("RES-NONEXISTENT")
        with self.assertRaises(ValueError):
            world_observations(self.bundle)

    def test_invalid_time_fails_closed(self):
        self.bundle["observations"][0]["observed_at"] = "yesterday"
        with self.assertRaises(ValueError):
            world_observations(self.bundle)

    def test_holdout_not_present_or_accepted(self):
        result = world_observations(self.bundle)
        self.assertNotIn("ground_truth_holdout", canonical_json(result))
        self.bundle["case_id"] = "REAL-TB-018"
        with self.assertRaises(ValueError):
            world_observations(self.bundle)


if __name__ == "__main__":
    unittest.main()
