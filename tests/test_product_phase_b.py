"""Product B: fixture-only local review notes, persistence and security tests."""
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from unittest.mock import patch
import uuid

from http.server import ThreadingHTTPServer

from apps.product.__main__ import ProductService, make_handler
from apps.product.review_store import (
    ReviewConflictError, ReviewStore, ReviewValidationError, snapshot_digest,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


def sample_bundle():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def new_draft(bundle):
    issue = bundle["exceptions"][0]
    return {
        "finding_index": 0,
        "finding_category": issue["category"],
        "evidence_record_ids": issue["evidence_record_ids"],
        "evidence_snapshot_sha256": snapshot_digest(bundle),
        "reviewer_label": "DEMO-REVIEWER",
        "disposition": "request_source_verification",
        "note": "Verify synthetic CASE-TB-018 against RES-TB-018; leave discrepancy unresolved.",
        "request_id": str(uuid.uuid4()),
    }


@contextmanager
def demo_server(service):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service)) as srv:
        t = Thread(target=srv.serve_forever, daemon=True)
        t.start()
        try:
            yield srv.server_address[1]
        finally:
            srv.shutdown()
            t.join(timeout=3)


def request(port, method, path, body=None, headers=None):
    con = http.client.HTTPConnection("127.0.0.1", port, timeout=6)
    con.request(method, path, body=body, headers=headers or {})
    result = con.getresponse()
    response = result.status, json.loads(result.read())
    con.close()
    return response


def post_review(port, draft, headers=None):
    return request(port, "POST", "/api/cases/CASE-TB-018/reviews",
                   body=json.dumps(draft).encode("utf-8"),
                   headers=headers or {
                       "Origin": f"http://127.0.0.1:{port}",
                       "Content-Type": "application/json",
                       "X-TBCareOS-Review-Intent": "record-human-admin-review-v1",
                   })


class ReviewStoreTests(unittest.TestCase):
    def test_snapshot_hash_is_stable_for_identical_evidence(self):
        a, b = sample_bundle(), sample_bundle()
        self.assertEqual(snapshot_digest(a), snapshot_digest(b))
        b["observations"][1]["source_record_id"] = "ROW-ORD-018-CHANGED"
        self.assertNotEqual(snapshot_digest(a), snapshot_digest(b))

    def test_persists_only_local_fictional_note_and_reopens_cleanly(self):
        with TemporaryDirectory() as directory:
            store = ReviewStore(directory)
            bundle = sample_bundle()
            record = store.record(bundle, new_draft(bundle))
            self.assertEqual(record["case_id"], "CASE-TB-018")
            self.assertEqual(record["kind"], "human_administrative_note")
            self.assertFalse(record["official_action_taken"])
            self.assertFalse(record["human_identity_verified"])
            self.assertEqual(record["evidence_record_ids"], ["CASE-TB-018", "RES-TB-018"])
            self.assertEqual(len(ReviewStore(directory).history("CASE-TB-018")), 1)
            self.assertEqual(len(ReviewStore(directory).activity()), 1)
            self.assertEqual(len(ReviewStore(directory).history("CASE-TB-001")), 0)
            self.assertEqual(
                (Path(directory) / "case-tb-018.jsonl").stat().st_mode & 0o777,
                0o600,
            )

    def test_duplicate_request_returns_same_record_without_new_event(self):
        with TemporaryDirectory() as directory:
            store = ReviewStore(directory)
            bundle = sample_bundle()
            draft = new_draft(bundle)
            original = store.record(bundle, draft)
            again = store.record(bundle, draft)
            self.assertEqual(original, again)
            self.assertEqual(len(store.history("CASE-TB-018")), 1)
            changed = {**draft, "note": "Another verification outcome remains unresolved."}
            with self.assertRaises(ReviewConflictError):
                store.record(bundle, changed)

    def test_rejects_stale_snapshot(self):
        with TemporaryDirectory() as directory:
            bundle = sample_bundle()
            draft = new_draft(bundle)
            bundle["observations"][1]["source_record_id"] = "ROW-ORD-018-MODIFIED"
            with self.assertRaises(ReviewConflictError):
                ReviewStore(directory).record(bundle, draft)
            self.assertEqual(list(Path(directory).glob("*")), [])

    def test_rejects_uncited_finding_and_non_demo_reviewer(self):
        with TemporaryDirectory() as directory:
            b = sample_bundle()
            good = new_draft(b)
            for field, bad in [
                ("finding_category", "clinical_outcome"),
                ("evidence_record_ids", ["RES-TB-999"]),
                ("finding_index", 999),
                ("reviewer_label", "Dr. Real Name"),
                ("disposition", "approve_care"),
            ]:
                with self.subTest(field=field):
                    draft = {**good, field: bad}
                    with self.assertRaises(ReviewValidationError):
                        ReviewStore(directory).record(b, draft)

    def test_rejects_clinical_text_real_identifiers_and_hallucinated_refs(self):
        with TemporaryDirectory() as directory:
            store, b = ReviewStore(directory), sample_bundle()
            for note in (
                "The patient missed treatment. CASE-TB-018.",
                "Please contact the patient with result RES-TB-018.",
                "Verify the real contact john@example.com.",
                "Refer to external source https://evil.example.",
                "Verify RES-TB-999 synthetic row for this case.",
                "Submit the SITB diagnosis result here.",
                "<img src=x onerror=alert(1)>",
            ):
                with self.subTest(note=note):
                    draft = new_draft(b)
                    draft["note"] = note
                    with self.assertRaises(ValueError):
                        store.record(b, draft)
            self.assertEqual(store.history("CASE-TB-018"), [])

    def test_short_gibberish_note_fails_structural_quality_check(self):
        with TemporaryDirectory() as directory:
            b = sample_bundle()
            draft = new_draft(b)
            draft["note"] = "sdfghjkhjkjhknijj"
            with self.assertRaisesRegex(ReviewValidationError, "at least four words"):
                ReviewStore(directory).record(b, draft)
            self.assertEqual(ReviewStore(directory).history("CASE-TB-018"), [])

    def test_corrupt_log_fails_closed_without_rewriting(self):
        with TemporaryDirectory() as directory:
            p = Path(directory) / "case-tb-018.jsonl"
            p.write_text("{bad json}\n")
            store = ReviewStore(directory)
            with self.assertRaises(ReviewValidationError):
                store.history("CASE-TB-018")
            with self.assertRaises(ReviewValidationError):
                store.record(sample_bundle(), new_draft(sample_bundle()))
            self.assertEqual(p.read_text(), "{bad json}\n")

    def test_rejects_real_case_id_and_invalid_request_uuid(self):
        with TemporaryDirectory() as directory:
            store = ReviewStore(directory)
            with self.assertRaises(ReviewValidationError):
                store.history("../../real_patient")
            draft = new_draft(sample_bundle())
            draft["request_id"] = "not-a-uuid"
            with self.assertRaises(ReviewValidationError):
                store.record(sample_bundle(), draft)


class ReviewAPITests(unittest.TestCase):
    def test_end_to_end_review_api_and_persistent_restart(self):
        with TemporaryDirectory() as directory:
            service = ProductService(helper=None, fixture=FIXTURE, review_dir=directory)
            with demo_server(service) as port:
                status, bundle = request(port, "GET", "/api/cases/CASE-TB-018/evidence")
                self.assertEqual(status, 200)
                self.assertEqual(len(bundle["evidence_snapshot_sha256"]), 64)
                status, empty = request(port, "GET", "/api/cases/CASE-TB-018/reviews")
                self.assertEqual(status, 200)
                self.assertEqual(empty["reviews"], [])
                draft = new_draft(sample_bundle())
                self.assertEqual(bundle["evidence_snapshot_sha256"], draft["evidence_snapshot_sha256"])
                status, entry = post_review(port, draft)
                self.assertEqual(status, 201)
                self.assertEqual(entry["finding_category"], "subject_mismatch")
                self.assertFalse(entry["official_action_taken"])
                status, record_again = post_review(port, draft)
                self.assertEqual(status, 201)
                self.assertEqual(record_again["review_event_id"], entry["review_event_id"])
                status, response = request(port, "GET", "/api/cases/CASE-TB-018/reviews")
                self.assertEqual(status, 200)
                self.assertEqual(len(response["reviews"]), 1)
                status, activity = request(port, "GET", "/api/review-activity")
                self.assertEqual(status, 200)
                self.assertEqual(activity["activity"][0]["recorded_notes"], 1)
            rebooted = ProductService(helper=None, fixture=FIXTURE, review_dir=directory)
            with demo_server(rebooted) as port:
                status, persisted = request(port, "GET", "/api/cases/CASE-TB-018/reviews")
                self.assertEqual(status, 200)
                self.assertEqual(len(persisted["reviews"]), 1)

    def test_refuses_cross_origin_review_no_intent_and_body_abuse(self):
        with TemporaryDirectory() as directory:
            service = ProductService(helper=None, fixture=FIXTURE, review_dir=directory)
            draft = new_draft(sample_bundle())
            with demo_server(service) as port:
                good_origin = f"http://127.0.0.1:{port}"
                standard = {
                    "Origin": good_origin,
                    "Content-Type": "application/json",
                    "X-TBCareOS-Review-Intent": "record-human-admin-review-v1",
                }
                variants = [
                    ({**standard, "Origin": "https://evil.example"}, 403),
                    ({**standard, "X-TBCareOS-Review-Intent": "wrong"}, 422),
                    ({**standard, "Content-Type": "text/plain"}, 422),
                    ({k: v for k, v in standard.items() if k != "Origin"}, 403),
                    ({**standard, "Host": "evil.example"}, 403),
                ]
                for headers, code in variants:
                    with self.subTest(headers=headers):
                        status, _ = post_review(port, draft, headers)
                        self.assertEqual(status, code)
                status, response = post_review(port, {**draft, "note": "Unsafe: john@example.com"})
                self.assertEqual(status, 422)
                self.assertEqual(response["error_code"], "review_validation_rejected")
                self.assertEqual(service.review_history("CASE-TB-018")["reviews"], [])

    def test_conflicting_source_snapshot_returns_409_without_appending(self):
        with TemporaryDirectory() as directory:
            service = ProductService(helper=None, fixture=FIXTURE, review_dir=directory)
            draft = new_draft(sample_bundle())
            draft["evidence_snapshot_sha256"] = "0" * 64
            with demo_server(service) as port:
                status, payload = post_review(port, draft)
                self.assertEqual(status, 409)
                self.assertEqual(payload["error_code"], "review_conflict")
                self.assertEqual(service.review_history("CASE-TB-018")["reviews"], [])


if __name__ == "__main__":
    unittest.main()
