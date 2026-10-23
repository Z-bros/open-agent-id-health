"""Product A API/UI smoke tests: no real provider, no HTTP external access."""
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
from threading import Thread
import unittest
from unittest.mock import patch

from http.server import ThreadingHTTPServer
from apps.product.__main__ import CASE_IDS, ProductService, make_handler, STATIC, public_failure
from apps.caselens.explain import CaseLensValidationError
from shared.inference.nemotron import NemotronError

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"


@contextmanager
def demo_server(service):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
            thread.join(timeout=3)


def make_request(port, method, path, body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    connection.request(method, path, body=body, headers=headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


class ProductTests(unittest.TestCase):
    def test_offline_fixture_exposes_only_real_saved_case(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        index = service.list_cases()
        self.assertEqual([c["case_id"] for c in index["cases"]], ["CASE-TB-018"])
        self.assertEqual(index["source_mode"], "saved_fixture")
        self.assertEqual(index["cases"][0]["evidence_status"], "not_checked")
        bundle = service.evidence("CASE-TB-018")
        self.assertEqual(bundle["case_id"], "CASE-TB-018")
        self.assertEqual(bundle["exceptions"][0]["category"], "subject_mismatch")
        with self.assertRaises(ValueError):
            service.evidence("CASE-TB-009")

    def test_inventory_advertises_synthetic_ids_without_guessing_availability(self):
        # Avoid constructing the production helper during unit testing.
        with patch("apps.product.__main__.ZetarisHelperClient", return_value=object()):
            service = ProductService(helper="/trusted/query_zetaris.py")
        index = service.list_cases()
        self.assertEqual(len(index["cases"]), 36)
        self.assertEqual(index["cases"][0]["case_id"], "CASE-TB-001")
        self.assertEqual(index["cases"][-1]["case_id"], "CASE-TB-036")
        self.assertTrue(all(x["evidence_status"] == "not_checked" for x in index["cases"]))
        self.assertEqual(len(CASE_IDS), 36)

    def test_http_static_assets_and_api(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        with demo_server(service) as port:
            for route in STATIC:
                with self.subTest(route=route):
                    status, headers, body = make_request(port, "GET", route)
                    self.assertEqual(status, 200)
                    self.assertIn(b"TB-CareOS" if route == "/" else b"", body)
                    self.assertIn("default-src 'self'", headers.get("Content-Security-Policy", ""))
            status, _, body = make_request(port, "GET", "/api/cases")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["cases"][0]["case_id"], "CASE-TB-018")
            status, _, body = make_request(port, "GET", "/api/cases/CASE-TB-018/evidence")
            self.assertEqual(status, 200)
            self.assertEqual(json.loads(body)["observations"][2]["record_id"], "RES-TB-018")
            status, _, body = make_request(port, "GET", "/api/not-a-route")
            self.assertEqual(status, 404)

    def test_http_disallows_cross_origin_or_mutations(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        with demo_server(service) as port:
            status, _, _ = make_request(port, "POST", "/api/cases/CASE-TB-018/explain",
                                 headers={"Origin": "https://evil.example"})
            self.assertEqual(status, 403)
            status, _, _ = make_request(port, "POST", "/api/cases/CASE-TB-018/plan",
                                 body='{"sql":"DELETE ALL"}',
                                 headers={"Content-Type": "application/json"})
            self.assertEqual(status, 400)
            for method in ("PUT", "PATCH", "DELETE"):
                status, _, _ = make_request(port, method, "/api/cases/CASE-TB-018/evidence")
                self.assertEqual(status, 405)
            status, _, body = make_request(port, "POST", "/api/cases/CASE-TB-999/plan")
            self.assertEqual(status, 400)
            self.assertIn(b"synthetic", body)

    def test_successful_agent_action_routes_delegate_without_mocking_results(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        sample_exp = {"case_id": "CASE-TB-018", "hypotheses": [], "requires_human_approval": True}
        sample_plan = {"case_id": "CASE-TB-018", "actions": [], "requires_human_approval": True}
        with patch.object(service, "explain", return_value=sample_exp) as exp, \
             patch.object(service, "plan", return_value=sample_plan) as plan:
            with demo_server(service) as port:
                status, _, body = make_request(port, "POST", "/api/cases/CASE-TB-018/explain")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), sample_exp)
                status, _, body = make_request(port, "POST", "/api/cases/CASE-TB-018/plan")
                self.assertEqual(status, 200)
                self.assertEqual(json.loads(body), sample_plan)
        exp.assert_called_once_with("CASE-TB-018")
        plan.assert_called_once_with("CASE-TB-018")

    def test_missing_server_nvidia_key_reports_actionable_safe_error(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        with patch.object(service, "explain", side_effect=NemotronError(
            "NVIDIA_API_KEY not set; create a key in NVIDIA Build and load it privately"
        )):
            with demo_server(service) as port:
                status, _, body = make_request(
                    port, "POST", "/api/cases/CASE-TB-018/explain"
                )
                self.assertEqual(status, 503)
                payload = json.loads(body)
                self.assertEqual(payload["error_code"], "nvidia_key_missing")
                self.assertIn("server process", payload["error"])
                self.assertIn("WSL", payload["next_step"])

    def test_provider_and_grounding_errors_are_distinct_without_raw_text(self):
        scenarios = [
            (NemotronError("NVIDIA API HTTP 403; private token 9876"),
             "nvidia_access_denied", 503),
            (NemotronError("NVIDIA API HTTP 404; private token 9876"),
             "nvidia_model_unavailable", 503),
            (NemotronError("NVIDIA API HTTP 429; private token 9876"),
             "nvidia_rate_limited", 503),
            (NemotronError("NVIDIA request timed out (configured timeout 75s)"),
             "nvidia_timeout", 503),
            (CaseLensValidationError("Unsafe hallucination: sk-live-SENSITIVE"),
             "agent_validation_rejected", 422),
        ]
        for exception, category, expected_status in scenarios:
            with self.subTest(category=category):
                status, code, message, guidance = public_failure(exception)
                self.assertEqual(status, expected_status)
                self.assertEqual(code, category)
                self.assertTrue(message and guidance)
                self.assertNotIn("9876", message + guidance)
                self.assertNotIn("sk-live-SENSITIVE", message + guidance)

    def test_external_model_error_never_leaks_provider_payload(self):
        service = ProductService(helper=None, fixture=FIXTURE)
        with patch.object(service, "explain", side_effect=RuntimeError(
            "provider error contains secret credential sk-live-SENSITIVE")):
            with demo_server(service) as port:
                status, _, body = make_request(port, "POST", "/api/cases/CASE-TB-018/explain")
                self.assertEqual(status, 500)
                self.assertIn(b"unexpected_internal_error", body)
                self.assertNotIn(b"sk-live-SENSITIVE", body)


if __name__ == "__main__":
    unittest.main()
