"""Offline E03 evidence-to-Meterless mapping and runner tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from shared.meterless.mapper import to_meterless_observations
from apps.careflow.tb_meterless import persist_bundle


def make_bundle():
    return {
        "schema_version": "1.0.0",
        "case_id": "CASE-TB-001",
        "observations": [
            {
                "record_id": "ORD-TB-001",
                "record_type": "lab_orders",
                "source_record_id": "ROW-ORD-001-A",
                "source_system": "LAB_SIM",
                "subject_ref": "SYN-SUBJ-001",
                "observed_at": "2026-09-01T11:00:00Z",
                "details": {"case_id": "CASE-TB-001", "source_table": "lab_orders"},
            },
            {
                "record_id": "CASE-TB-001",
                "record_type": "cases",
                "source_record_id": "CASE-TB-001",
                "source_system": "CASES_SIM",
                "subject_ref": "SYN-SUBJ-001",
                "observed_at": "2026-09-01T08:00:00Z",
                "details": {"case_id": "CASE-TB-001", "source_table": "cases"},
            },
        ],
        "exceptions": [],
        "source_checks": [
            {"source_system": "cases", "attempt": 1, "status": "available"},
        ],
        "requires_human_approval": True,
    }


class MapperTests(unittest.TestCase):
    def test_stable_mappings_after_reordered_source_rows(self):
        bundle = make_bundle()
        first = to_meterless_observations(bundle)
        bundle["observations"].reverse()
        second = to_meterless_observations(bundle)
        self.assertEqual(first, second)
        self.assertEqual(len(first), 3)
        self.assertEqual(len(set(x["externalId"] for x in first)), 3)

    def test_source_id_and_subject_preserved_in_text(self):
        mapped = to_meterless_observations(make_bundle())
        evidence = [x for x in mapped if x["type"] == "tb_evidence"]
        self.assertEqual(len(evidence), 2)
        doc = json.loads([e for e in evidence if e["title"].startswith("lab_orders:")][0]["text"])
        self.assertEqual(doc["source_record_id"], "ROW-ORD-001-A")
        self.assertEqual(doc["subject_ref"], "SYN-SUBJ-001")
        self.assertEqual(doc["case_id"], "CASE-TB-001")

    def test_derived_summary_discloses_timestamp_basis(self):
        mapped = to_meterless_observations(make_bundle())
        summary = [x for x in mapped if x["type"] == "tb_investigation"][0]
        content = json.loads(summary["text"])
        self.assertEqual(content["timestamp_basis"], "latest_source_observation_not_query_time")
        self.assertTrue(content["requires_human_approval"])

    def test_changed_exception_preserves_new_investigation_id(self):
        bundle = make_bundle()
        original = [x["externalId"] for x in to_meterless_observations(bundle)
                    if x["type"] == "tb_investigation"][0]
        bundle["exceptions"].append({
            "category": "subject_mismatch", "description": "Synthetic mismatch",
            "evidence_record_ids": ["CASE-TB-001", "ORD-TB-001"],
        })
        changed = [x["externalId"] for x in to_meterless_observations(bundle)
                   if x["type"] == "tb_investigation"][0]
        self.assertNotEqual(original, changed)

    def test_mismatched_case_rejected(self):
        bundle = make_bundle()
        bundle["observations"][0]["details"]["case_id"] = "CASE-TB-002"
        with self.assertRaises(ValueError):
            to_meterless_observations(bundle)

    def test_duplicate_provenance_rejected(self):
        bundle = make_bundle()
        bundle["observations"].append(dict(bundle["observations"][0]))
        with self.assertRaises(ValueError):
            to_meterless_observations(bundle)

    def test_missing_human_review_rejected(self):
        bundle = make_bundle()
        bundle["requires_human_approval"] = False
        with self.assertRaises(ValueError):
            to_meterless_observations(bundle)

    def test_invalid_timestamp_rejected(self):
        bundle = make_bundle()
        bundle["observations"][0]["observed_at"] = "some-date"
        with self.assertRaises(ValueError):
            to_meterless_observations(bundle)

    def test_runner_sends_actual_mapped_batch_as_stdin(self):
        with TemporaryDirectory() as directory:
            ref = Path(directory) / "reference"
            (ref / "src").mkdir(parents=True)
            (ref / "node_modules/.bin").mkdir(parents=True)
            (ref / "src/index.ts").write_text("export class WorldModel {}", encoding="utf-8")
            (ref / "node_modules/.bin/tsx").write_text("", encoding="utf-8")
            report = {
                "replay": {"projection_unchanged": True},
                "persisted_projection_matches": True,
            }
            class Completed:
                returncode = 0
                stdout = json.dumps(report)
                stderr = ""
            with patch("apps.careflow.tb_meterless.subprocess.run", return_value=Completed) as run:
                result = persist_bundle(make_bundle(), reference=ref, state_dir=directory)
            self.assertTrue(result["persisted_projection_matches"])
            actual = json.loads(run.call_args.kwargs["input"])
            self.assertEqual(len(actual), 3)
            self.assertTrue(run.call_args.kwargs["capture_output"])
            self.assertFalse(run.call_args.kwargs["check"])

    def test_runner_refuses_failed_replay(self):
        with TemporaryDirectory() as directory:
            ref = Path(directory)
            (ref / "src").mkdir()
            (ref / "node_modules/.bin").mkdir(parents=True)
            (ref / "src/index.ts").write_text("export class WorldModel {}", encoding="utf-8")
            (ref / "node_modules/.bin/tsx").write_text("", encoding="utf-8")
            class Completed:
                returncode = 0
                stdout = json.dumps({"replay": {"projection_unchanged": False},
                                     "persisted_projection_matches": True})
            with patch("apps.careflow.tb_meterless.subprocess.run", return_value=Completed):
                with self.assertRaises(RuntimeError):
                    persist_bundle(make_bundle(), reference=ref, state_dir=directory)


if __name__ == "__main__":
    unittest.main()
