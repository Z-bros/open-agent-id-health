"""Phase C: local read-only audit index, actual-case boundaries, no invented events."""
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from http.server import ThreadingHTTPServer
from apps.product.__main__ import ProductService, make_handler
from apps.product.audit_reader import AuditReadError, MeterlessAuditReader

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


def audit_payload():
    return {
        "schema_version": "1.0.0",
        "kind": "meterless_world_model_event_index",
        "case_id": "CASE-TB-018",
        "namespace": "tbcareos_case_tb_018",
        "store": "real_meterless_reference",
        "event_count": 24,
        "audit_count": 22,
        "has_persisted_events": True,
        "events": [
            {"event_id": "evt_24", "event_type": "relate",
             "event_at": "2026-09-19T23:00:00.000Z"},
        ],
        "truncated": True,
        "source": "local_meterless_world_model",
        "timestamp_meaning":
            "Synthetic evidence snapshot/event time, not agent invocation or human-review time",
    }


@contextmanager
def serve(service):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service)) as srv:
        thread = Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        try:
            yield srv.server_address[1]
        finally:
            srv.shutdown()
            thread.join(timeout=3)


def request(port, path):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", path)
    response = conn.getresponse()
    result = response.status, json.loads(response.read())
    conn.close()
    return result


class AuditTests(unittest.TestCase):
    def test_api_returns_only_reader_data_without_writes_or_inference(self):
        with TemporaryDirectory() as local:
            service = ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            with patch.object(service.audit_reader, "read", return_value=audit_payload()) as audit:
                with serve(service) as port:
                    status, response = request(port, "/api/cases/CASE-TB-018/audit")
                    self.assertEqual(status, 200)
                    self.assertEqual(response, audit_payload())
                    status, _ = request(port, "/api/cases/CASE-TB-999/audit")
                    self.assertEqual(status, 422)
            audit.assert_called_once_with("CASE-TB-018")

    def test_api_reports_not_installed_audit_without_inventing_events(self):
        with TemporaryDirectory() as local:
            service = ProductService(
                helper=None, fixture=FIXTURE, review_dir=local,
                meterless_reference=Path(local) / "not-installed",
                meterless_state_dir=Path(local) / "absent",
            )
            with serve(service) as port:
                status, data = request(port, "/api/cases/CASE-TB-018/audit")
                self.assertEqual(status, 503)
                self.assertEqual(data["error_code"], "meterless_audit_unavailable")
                self.assertNotIn("events", data)

    def test_reader_checks_real_upstream_installation(self):
        with TemporaryDirectory() as local:
            reader = MeterlessAuditReader(
                reference=Path(local) / "upstream",
                state_dir=Path(local) / "state",
            )
            with self.assertRaises(AuditReadError):
                reader.read("CASE-TB-018")
            with self.assertRaises(ValueError):
                reader.read("CASE-TB-999")

    def test_reader_never_accepts_wrong_case_or_fake_events(self):
        with TemporaryDirectory() as local:
            root=Path(local)
            ref=root / "reference"
            (ref / "src").mkdir(parents=True)
            (ref / "src/index.ts").write_text("// test reference")
            (ref / "node_modules/.bin").mkdir(parents=True)
            (ref / "node_modules/.bin/tsx").write_text("# fake tsx test runner")
            state=root / "state"
            state.mkdir()
            reader=MeterlessAuditReader(ref,state)
            issues=[
                {"case_id":"CASE-TB-099"},
                {"event_count":-1},
                {"store":"fabricated-mock"},
                {"events":[{"event_id":"evt_bad", "event_type":"relate", "event_at":"2026-09-19T23:00:00Z"}]},
                {"events":[{"event_id":"evt_1", "event_type":"<script>", "event_at":"2026-09-19T23:00:00Z"}]},
            ]
            for altered in issues:
                payload={**audit_payload(),**altered}
                with self.subTest(altered=altered):
                    with patch("apps.product.audit_reader.subprocess.run",
                               return_value=SimpleNamespace(
                                   returncode=0,stdout=json.dumps(payload),stderr="",
                               )):
                        with self.assertRaises(AuditReadError):
                            reader.read("CASE-TB-018")
            with patch("apps.product.audit_reader.subprocess.run",
                       return_value=SimpleNamespace(
                           returncode=0,stdout=json.dumps(audit_payload()),stderr="",
                       )) as run:
                received=reader.read("CASE-TB-018")
                self.assertEqual(received["event_count"],24)
                arguments=run.call_args.args[0]
                self.assertNotIn("ingest", " ".join(arguments))
                self.assertIn("--case-id", arguments)

    def test_audit_does_not_mutate_existing_local_reviewer_ledger(self):
        with TemporaryDirectory() as local:
            service=ProductService(helper=None,fixture=FIXTURE,review_dir=local)
            with patch.object(service.audit_reader,"read",side_effect=AuditReadError("offline")):
                with serve(service) as port:
                    request(port,"/api/cases/CASE-TB-018/audit")
                self.assertEqual(list(Path(local).iterdir()),[])


if __name__=="__main__":
    unittest.main()
