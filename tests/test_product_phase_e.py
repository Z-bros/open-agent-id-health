"""Product E: explicit provider JSON mode and humane fail-closed UI contract."""
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from urllib.error import HTTPError

from apps.caselens.explain import CaseLensValidationError
from apps.product.__main__ import ProductService, public_failure
from shared.inference.nemotron import (
    NVIDIAChatClient, NemotronError, LIGHTNING_MODEL,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "tb_case_018_bundle.json"
JS = (ROOT / "apps/product/web/app.js").read_text(encoding="utf-8")
CSS = (ROOT / "apps/product/web/style.css").read_text(encoding="utf-8")
MESSAGES = [
    {"role": "system", "content": "Return only a JSON object."},
    {"role": "user", "content": "Synthetic admin evidence, no real patient."},
]


class Reply:
    def __init__(self, payload: dict):
        self.body = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return io.BytesIO(self.body)

    def __exit__(self, exc_type, exc, tb):
        return False


class ProviderJSONModeTests(unittest.TestCase):
    def test_case_lens_json_request_has_explicit_format_and_thinking_disabled(self):
        observed = []
        def urlopen(req, timeout):
            observed.append(json.loads(req.data))
            return Reply({
                "choices": [{"finish_reason": "stop", "message": {
                    "content": '{"explanations":[]}'}}],
            })
        with patch("shared.inference.nemotron.urllib.request.urlopen", side_effect=urlopen):
            client = NVIDIAChatClient(api_key="test-private-key",
                                      model=LIGHTNING_MODEL, json_output=True)
            response = client.complete(MESSAGES)
        self.assertEqual(response, '{"explanations":[]}')
        self.assertEqual(observed[0]["response_format"], {"type": "json_object"})
        self.assertEqual(observed[0]["chat_template_kwargs"], {"enable_thinking": False})
        self.assertFalse(observed[0]["stream"])
        self.assertNotIn("test-private-key", json.dumps(observed))

    def test_plain_transport_remains_unchanged_for_nextstep(self):
        observed = []
        def urlopen(req, timeout):
            observed.append(json.loads(req.data))
            return Reply({"choices": [{"finish_reason": "stop",
                                       "message": {"content": '{"selected_query_ids":[]}'}}]})
        with patch("shared.inference.nemotron.urllib.request.urlopen", side_effect=urlopen):
            answer = NVIDIAChatClient(api_key="test-key", model=LIGHTNING_MODEL).complete(MESSAGES)
        self.assertIn("selected_query_ids", answer)
        self.assertNotIn("response_format", observed[0])

    def test_json_mode_rejects_incomplete_or_non_json_outputs(self):
        for reason, content in [
            ("length", '{"explanations":['),
            ("stop", "not JSON"),
            (None, '{"explanations":[]}'),
        ]:
            with self.subTest(reason=reason, content=content):
                with patch("shared.inference.nemotron.urllib.request.urlopen",
                           return_value=Reply({"choices": [
                               {"finish_reason": reason, "message": {"content": content}}
                           ]})):
                    with self.assertRaises(NemotronError):
                        NVIDIAChatClient(api_key="test-key", model=LIGHTNING_MODEL,
                                         json_output=True).complete(MESSAGES)

    def test_unsupported_provider_feature_fails_visible_without_substitute(self):
        error = HTTPError(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            422, "unsupported test", None, io.BytesIO(b"private-token"),
        )
        with patch("shared.inference.nemotron.urllib.request.urlopen",
                   side_effect=error):
            with self.assertRaisesRegex(NemotronError, "NVIDIA API HTTP 422"):
                NVIDIAChatClient(api_key="test-key", model=LIGHTNING_MODEL,
                                 json_output=True).complete(MESSAGES)
        status, category, message, guidance = public_failure(NemotronError("NVIDIA API HTTP 422"))
        self.assertEqual(status, 503)
        self.assertEqual(category, "nvidia_provider_error")
        self.assertNotIn("private-token", message + guidance)

    def test_json_mode_argument_is_explicit_boolean(self):
        with self.assertRaises(ValueError):
            NVIDIAChatClient(api_key="test", json_output="yes")


class CaseLensProductTests(unittest.TestCase):
    def test_product_enables_json_only_for_caselens(self):
        with TemporaryDirectory() as tmp:
            service=ProductService(helper=None, fixture=FIXTURE, review_dir=tmp)
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with patch("apps.product.__main__.describe_case",
                           return_value={"case_id":"CASE-TB-018"}) as call:
                    service.explain("CASE-TB-018")
                    call.assert_called_once()
                    self.assertEqual(model.call_args.kwargs.get("json_output"), True)
                with patch("apps.product.__main__.plan_case",
                           return_value={"case_id":"CASE-TB-018"}):
                    service.plan("CASE-TB-018")
                    self.assertNotIn("json_output", model.call_args.kwargs)

    def test_public_error_codes_never_echo_untrusted_model_text(self):
        cases = [
            ("Nemotron returned an invalid top-level structure", "caselens_structure"),
            ("Nemotron did not return strict JSON", "caselens_invalid_json"),
            ("Nemotron cited a non-retrieved event or source record",
             "caselens_unretrieved_citation"),
        ]
        for reason, expected in cases:
            with self.subTest(reason=reason):
                status, category, message, guidance = public_failure(
                    CaseLensValidationError(reason)
                )
                self.assertEqual(status, 422)
                self.assertEqual(category, expected)
                self.assertTrue(message and guidance)
        status, category, message, guidance = public_failure(
            CaseLensValidationError("Raw model secret sk-private-token")
        )
        self.assertEqual(category, "agent_validation_rejected")
        self.assertNotIn("sk-private-token", message + guidance)

    def test_ui_failure_retry_is_opt_in_and_never_fakes_result(self):
        self.assertIn('function renderAgentFailure(kind, error)', JS)
        self.assertIn('retry.addEventListener("click",()=>invokeAgent(kind))', JS)
        self.assertIn('inspect.addEventListener("click",()=>navigateSection("findings-card"))', JS)
        self.assertIn("No substitute result was generated", JS)
        self.assertIn('"nvidia_key_missing","nvidia_access_denied","nvidia_model_unavailable"', JS)
        self.assertIn(".agent-grid{align-items:start}", CSS)
        begin=JS.index("async function loadCase(id)")
        end=JS.index("function renderExplanation(",begin)
        self.assertNotIn("invokeAgent(", JS[begin:end])


if __name__=="__main__":
    unittest.main()
