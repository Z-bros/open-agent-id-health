"""Product Phase D source snapshot version-binding tests."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from contextlib import contextmanager
import http.client
from http.server import ThreadingHTTPServer
from threading import Thread

from apps.product.__main__ import (
    EvidenceSnapshotChanged, ProductService, make_handler, public_failure,
)

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


@contextmanager
def server(service):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service)) as httpd:
        thread = Thread(target=httpd.serve_forever, daemon=True)
        thread.start()
        try:
            yield httpd.server_address[1]
        finally:
            httpd.shutdown()
            thread.join(timeout=3)


def post(port, path, headers):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=6)
    connection.request("POST", path, headers=headers)
    response = connection.getresponse()
    status, payload = response.status, json.loads(response.read())
    connection.close()
    return status, payload


class SnapshotBindingTests(unittest.TestCase):
    def test_server_refuses_stale_snapshot_before_constructing_model(self):
        with TemporaryDirectory() as local:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            expected=service.evidence_response("CASE-TB-018")["evidence_snapshot_sha256"]
            self.assertEqual(len(expected), 64)
            wrong="0" * 64
            self.assertNotEqual(expected, wrong)
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with self.assertRaises(EvidenceSnapshotChanged):
                    service.explain("CASE-TB-018", expected_snapshot=wrong)
                with self.assertRaises(EvidenceSnapshotChanged):
                    service.plan("CASE-TB-018", expected_snapshot=wrong)
                model.assert_not_called()

    def test_api_returns_409_and_safe_recovery_guidance(self):
        with TemporaryDirectory() as local:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with server(service) as port:
                    for endpoint in ("explain", "plan"):
                        status, data=post(
                            port, f"/api/cases/CASE-TB-018/{endpoint}",
                            {"X-TBCareOS-Evidence-SHA256":"0"*64},
                        )
                        self.assertEqual(status, 409)
                        self.assertEqual(data["error_code"], "evidence_snapshot_changed")
                        self.assertIn("Refresh", data["next_step"])
                        self.assertNotIn("token", json.dumps(data).lower())
                model.assert_not_called()

    def test_correct_snapshot_uses_same_retrieved_bundle(self):
        with TemporaryDirectory() as local:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            digest=service.evidence_response("CASE-TB-018")["evidence_snapshot_sha256"]
            sentinel={"case_id":"CASE-TB-018", "requires_human_approval":True}
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with patch("apps.product.__main__.describe_case", return_value=sentinel) as description:
                    self.assertEqual(service.explain("CASE-TB-018",digest),sentinel)
                    self.assertEqual(description.call_args.args[0]["case_id"],"CASE-TB-018")
                with patch("apps.product.__main__.plan_case", return_value=sentinel) as planner:
                    self.assertEqual(service.plan("CASE-TB-018",digest),sentinel)
                    self.assertEqual(planner.call_args.args[0]["case_id"],"CASE-TB-018")
                self.assertEqual(model.call_count,2)

    def test_invalid_snapshot_fails_without_model(self):
        with TemporaryDirectory() as local:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with self.assertRaises(ValueError):
                    service.explain("CASE-TB-018","invalid-snapshot")
                model.assert_not_called()

    def test_original_api_without_snapshot_retains_supported_behavior(self):
        # Backward compatibility for E04/E05 and explicit tests that invoke
        # the model without a browser snapshot. This is not a production
        # requirement to trust unbound requests.
        with TemporaryDirectory() as local:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            with patch("apps.product.__main__.NVIDIAChatClient"):
                with patch("apps.product.__main__.describe_case",
                           return_value={"case_id":"CASE-TB-018"}) as handler:
                    service.explain("CASE-TB-018")
                    self.assertEqual(handler.call_count,1)

    def test_ui_sends_evidence_hash_and_disables_actions_when_stale(self):
        js=(Path(__file__).resolve().parents[1] / "apps/product/web/app.js").read_text()
        self.assertIn('"X-TBCareOS-Evidence-SHA256":state.evidence.evidence_snapshot_sha256',js)
        self.assertIn('if(error.code==="evidence_snapshot_changed")',js)
        self.assertIn('state.workflow.evidence="stale"',js)
        self.assertIn('state.workflow.evidence!=="retrieved"',js)


if __name__=="__main__":
    unittest.main()
