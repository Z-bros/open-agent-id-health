"""Post-kickoff offline reconciliation tests; no Zetaris or holdout required."""
import json
from pathlib import Path
import unittest

from apps.careflow.reconcile import reconcile_case
from shared.zetaris.readonly import ZetarisQueryError


def case_rows(*, due="2026-09-04T11:00:00Z"):
    cid, subj = "CASE-TB-001", "SYN-SUBJ-001"
    base = {
        "cases": [{
            "case_id": cid, "subject_ref": subj,
            "opened_at": "2026-09-01T08:00:00Z",
            "review_cutoff_at": "2026-10-20T12:05:00Z",
            "admin_result_expected_by": due,
            "admin_followup_expected_by": "2026-09-06T11:00:00Z",
        }],
        "screening_events": [{
            "ingest_row_id": "ROW-SCR-001-A", "event_id": "SCR-TB-001", "case_id": cid,
            "subject_ref": subj, "source_system": "SCREENING_SIM",
            "recorded_at": "2026-09-01T08:00:00Z",
            "linked_order_id": "ORD-TB-001",
        }],
        "lab_orders": [{
            "ingest_row_id": "ROW-ORD-001-A", "order_id": "ORD-TB-001", "case_id": cid,
            "subject_ref": subj, "source_system": "LAB_SIM",
            "ordered_at": "2026-09-01T11:00:00Z",
            "screening_event_id": "SCR-TB-001",
        }],
        "lab_results": [{
            "ingest_row_id": "ROW-RES-001-A", "result_id": "RES-TB-001", "case_id": cid,
            "subject_ref": subj, "source_system": "LAB_SIM",
            "released_at": "2026-09-02T11:00:00Z", "order_id": "ORD-TB-001",
            "result_token": "SYNTHETIC_TOKEN_NO_CLINICAL_MEANING",
        }],
        "followup_events": [{
            "ingest_row_id": "ROW-FUP-001-A", "followup_event_id": "FUP-TB-001",
            "case_id": cid, "subject_ref": subj, "source_system": "FOLLOWUP_SIM",
            "documented_at": "2026-09-02T23:00:00Z",
            "order_id": "ORD-TB-001", "result_id": "RES-TB-001",
        }],
    }
    return base


class FakeZetaris:
    def __init__(self, rows, errors=None):
        self.rows = rows
        self.errors = errors or {}
        self.queries = []

    def query(self, sql):
        self.queries.append(sql)
        table = sql.split(" FROM ", 1)[1].split(".", 1)[1].split(" ", 1)[0]
        if table in self.errors:
            raise ZetarisQueryError(self.errors[table], "simulated error")
        return list(self.rows[table])


class ReconciliationTests(unittest.TestCase):
    def run_case(self, rows, errors=None):
        client = FakeZetaris(rows, errors)
        result = reconcile_case(client, namespace="TBCARE_OS", case_id="CASE-TB-001")
        self.assertEqual(len(client.queries), 5)
        self.assertTrue(all("TBCARE_OS." in s for s in client.queries))
        return result

    def test_complete_returns_five_provenanced_observations(self):
        output = self.run_case(case_rows())
        self.assertEqual(output["schema_version"], "1.0.0")
        self.assertEqual(len(output["observations"]), 5)
        self.assertEqual(output["exceptions"], [])
        self.assertTrue(output["requires_human_approval"])
        self.assertEqual(output["observations"][3]["source_record_id"], "ROW-RES-001-A")
        self.assertEqual(output["observations"][3]["record_id"], "RES-TB-001")
        self.assertNotIn("SYNTHETIC_TOKEN", json.dumps(output))

    def test_output_matches_existing_contract_shape(self):
        result = self.run_case(case_rows())
        path = Path(__file__).resolve().parents[1] / "shared/contracts/evidence_bundle.v1.schema.json"
        schema = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(set(result), set(schema["properties"]))
        self.assertTrue(set(schema["required"]).issubset(result))
        for field in ("observations", "exceptions", "source_checks"):
            child_schema = schema["properties"][field]["items"]
            for item in result[field]:
                self.assertTrue(set(child_schema["required"]).issubset(item))
                self.assertTrue(set(item).issubset(child_schema["properties"]))

    def test_missing_lab_document_is_unverified_not_clinical(self):
        rows = case_rows()
        rows["lab_results"] = []
        rows["followup_events"] = []
        result = self.run_case(rows)
        categories = {e["category"] for e in result["exceptions"]}
        self.assertIn("lab_document_not_found_in_query", categories)
        self.assertNotIn("followup_document_not_found_in_query", categories)
        description = result["exceptions"][0]["description"]
        self.assertIn("snapshot completeness", description)
        self.assertEqual(result["source_checks"][3]["status"], "not_found")

    def test_subject_mismatch_is_provenance_cited(self):
        rows = case_rows()
        rows["lab_results"][0]["subject_ref"] = "SYN-SUBJ-999"
        result = self.run_case(rows)
        flagged = [x for x in result["exceptions"] if x["category"] == "subject_mismatch"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(set(flagged[0]["evidence_record_ids"]), {"CASE-TB-001", "RES-TB-001"})

    def test_unreachable_source_never_becomes_missing_document(self):
        rows = case_rows()
        result = self.run_case(rows, {"lab_results": "temporarily_unavailable"})
        categories = {e["category"] for e in result["exceptions"]}
        self.assertIn("source_query_unavailable", categories)
        self.assertNotIn("lab_document_not_found_in_query", categories)
        self.assertEqual(result["source_checks"][3]["status"], "temporarily_unavailable")

    def test_pending_not_due_has_no_missing_lab_exception(self):
        rows = case_rows(due="2026-11-04T11:00:00Z")
        rows["lab_results"] = []
        rows["followup_events"] = []
        result = self.run_case(rows)
        self.assertFalse(any(x["category"] == "lab_document_not_found_in_query"
                             for x in result["exceptions"]))

    def test_duplicate_ingest_preserves_both_source_ids(self):
        rows = case_rows()
        row = dict(rows["lab_results"][0])
        row["ingest_row_id"] = "ROW-RES-001-B"
        rows["lab_results"].append(row)
        result = self.run_case(rows)
        self.assertIn("duplicate_business_event_replay",
                      {x["category"] for x in result["exceptions"]})
        references = [x["source_record_id"] for x in result["observations"]
                      if x["record_type"] == "lab_results"]
        self.assertEqual(set(references), {"ROW-RES-001-A", "ROW-RES-001-B"})

    def test_wrong_result_order_is_link_mismatch(self):
        rows = case_rows()
        rows["lab_results"][0]["order_id"] = "ORD-NONMATCH"
        result = self.run_case(rows)
        flagged = [x for x in result["exceptions"]
                   if x["category"] == "cross_source_link_mismatch"]
        self.assertEqual(len(flagged), 1)
        self.assertEqual(flagged[0]["evidence_record_ids"], ["RES-TB-001"])

    def test_permission_denial_preserves_denial(self):
        result = self.run_case(case_rows(), {"lab_results": "permission_denied"})
        self.assertEqual(result["source_checks"][3]["status"], "permission_denied")
        self.assertNotIn("lab_document_not_found_in_query",
                         {x["category"] for x in result["exceptions"]})

    def test_missing_registry_is_not_treated_as_a_confirmed_case(self):
        rows = case_rows()
        rows["cases"] = []
        result = self.run_case(rows)
        self.assertIn("case_reference_unverified",
                      {x["category"] for x in result["exceptions"]})
        self.assertNotIn("lab_document_not_found_in_query",
                         {x["category"] for x in result["exceptions"]})

    def test_bad_timestamp_fails_closed(self):
        rows = case_rows()
        rows["lab_results"][0]["released_at"] = "not-a-date"
        result = self.run_case(rows)
        self.assertEqual(result["source_checks"][3]["status"], "error")
        self.assertIn("source_query_unavailable", {x["category"] for x in result["exceptions"]})


if __name__ == "__main__":
    unittest.main()
