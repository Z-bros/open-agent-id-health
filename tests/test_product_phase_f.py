"""Product F: exact CaseLens output contract while keeping strict rejection."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import io
import json
import unittest

from apps.caselens.explain import CaseLensValidationError, SYSTEM_PROMPT, describe_case
from apps.product.__main__ import ProductService
from shared.inference.nemotron import NVIDIAChatClient, LIGHTNING_MODEL

FIXTURE = Path(__file__).parent / "fixtures" / "tb_case_018_bundle.json"


class EchoModel:
    def __init__(self, extra=False):
        self.sent = None
        self.extra = extra

    def complete(self, messages):
        self.sent = json.loads(messages[-1]["content"].split("\n", 1)[1])
        result = []
        for finding in self.sent["careflow_findings"]:
            ids = finding["evidence_record_ids"]
            subject_refs = sorted({
                e["subject_ref"] for e in self.sent["evidence"]
                if e["record_id"] in ids
            })
            text = ("Retrieved administrative records " + " and ".join(ids) +
                    " require verification against these synthetic source entries.")
            if finding["category"] == "subject_mismatch":
                text += " The conflicting source subjects are " + " and ".join(subject_refs) + "."
            item = {
                "finding_index": finding["finding_index"],
                "reason": text,
                "unresolved_question": "Which cited synthetic source record needs manual verification?",
            }
            if self.extra:
                item["evidence_record_ids"] = ids
            result.append(item)
        return json.dumps({"explanations": result})


class CaseLensContractTests(unittest.TestCase):
    def test_responds_to_app_owned_exact_template(self):
        model = EchoModel()
        result = describe_case(json.loads(FIXTURE.read_text()), model)
        self.assertEqual(result["hypotheses"][0]["assessment"], "supported")
        template = model.sent["required_output_shape"]
        self.assertEqual(template, {"explanations": [
            {"finding_index": 0, "reason": "", "unresolved_question": ""}
        ]})
        self.assertNotIn("provisional_assessment", json.dumps(model.sent))
        self.assertEqual(
            set(model.sent["careflow_findings"][0]),
            {"finding_index", "category", "careflow_description", "evidence_record_ids"},
        )
        self.assertIn("EXACTLY these three keys", SYSTEM_PROMPT)

    def test_unapproved_model_fields_are_still_rejected(self):
        model = EchoModel(extra=True)
        with self.assertRaisesRegex(CaseLensValidationError, "not allowlisted"):
            describe_case(json.loads(FIXTURE.read_text()), model)

    def test_product_only_changes_caselens_sampling(self):
        with TemporaryDirectory() as local:
            product = ProductService(helper=None, fixture=FIXTURE, review_dir=local)
            with patch("apps.product.__main__.NVIDIAChatClient") as client:
                with patch("apps.product.__main__.describe_case",
                           return_value={"case_id": "CASE-TB-018"}):
                    product.explain("CASE-TB-018")
                self.assertEqual(
                    client.call_args.kwargs,
                    {"model": product.model, "json_output": True, "temperature": 0.0},
                )
                with patch("apps.product.__main__.plan_case",
                           return_value={"case_id": "CASE-TB-018"}):
                    product.plan("CASE-TB-018")
                self.assertEqual(client.call_args.kwargs, {"model": product.model})

    def test_provider_payload_respects_explicit_sampling(self):
        sent = []
        class Reply:
            def __enter__(self):
                return io.BytesIO(json.dumps({
                    "choices": [{"finish_reason": "stop", "message": {
                        "content": '{"explanations":[]}'}}],
                }).encode())
            def __exit__(self, *args):
                return False
        def urlopen(req, timeout):
            sent.append(json.loads(req.data))
            return Reply()
        with patch("shared.inference.nemotron.urllib.request.urlopen", side_effect=urlopen):
            NVIDIAChatClient(api_key="synthetic-test", model=LIGHTNING_MODEL,
                             json_output=True, temperature=0.0).complete([
                                 {"role": "system", "content": "Return JSON."},
                                 {"role": "user", "content": "Synthetic test only."},
                             ])
        self.assertEqual(sent[0]["temperature"], 0.0)
        self.assertEqual(sent[0]["response_format"], {"type": "json_object"})
        with self.assertRaises(ValueError):
            NVIDIAChatClient(api_key="test", temperature=True)
        with self.assertRaises(ValueError):
            NVIDIAChatClient(api_key="test", temperature=1.5)


if __name__ == "__main__":
    unittest.main()
