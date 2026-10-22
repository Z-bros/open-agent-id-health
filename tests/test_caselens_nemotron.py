"""Offline E04 CaseLens tests; NO real NVIDIA calls and NO held-out labels."""
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from unittest.mock import patch
import unittest

from apps.caselens.explain import CaseLensValidationError, describe_case
from apps.caselens.__main__ import main
from shared.inference.nemotron import NVIDIAChatClient, NemotronError

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/tb_case_018_bundle.json"


def sample_response(*, reason=None, question=None, index=0):
    reason = reason or (
        "The registry CASE-TB-018 lists SYN-SUBJ-018, but result RES-TB-018 "
        "lists SYN-SUBJ-999; the administrative subject association remains "
        "unverified and needs human review."
    )
    question = question or (
        "Can a human reviewer verify RES-TB-018 against the synthetic "
        "registry CASE-TB-018?"
    )
    return json.dumps({"explanations": [{
        "finding_index": index,
        "reason": reason,
        "unresolved_question": question,
    }]})


class Stub:
    def __init__(self, text):
        self.text = text
        self.calls = []

    def complete(self, messages):
        self.calls.append(messages)
        return self.text


class CaseLensTests(unittest.TestCase):
    def setUp(self):
        self.bundle = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_subject_mismatch_exact_citations(self):
        stub = Stub(sample_response())
        report = describe_case(self.bundle, stub)
        self.assertEqual(set(report), {
            "schema_version", "case_id", "hypotheses",
            "unresolved_questions", "requires_human_approval",
        })
        self.assertTrue(report["requires_human_approval"])
        self.assertEqual(len(report["hypotheses"]), 1)
        finding = report["hypotheses"][0]
        self.assertEqual(finding["assessment"], "supported")
        self.assertEqual(finding["hypothesis"], "Administrative review finding: subject_mismatch")
        self.assertEqual(finding["evidence_record_ids"], ["CASE-TB-018", "RES-TB-018"])
        self.assertIn("SYN-SUBJ-999", finding["reason"])
        self.assertEqual(stub.calls[0][0]["role"], "system")
        self.assertNotIn("ground_truth_holdout", json.dumps(stub.calls))
        self.assertNotIn("result_token", json.dumps(stub.calls))

    def test_matches_preexisting_explanation_contract(self):
        report = describe_case(self.bundle, Stub(sample_response()))
        schema = json.loads((ROOT / "shared/contracts/explanation_report.v1.schema.json").read_text())
        self.assertEqual(set(report), set(schema["properties"]))
        self.assertTrue(set(schema["required"]) <= set(report))
        for h in report["hypotheses"]:
            rule = schema["properties"]["hypotheses"]["items"]
            self.assertTrue(set(rule["required"]) <= set(h))
            self.assertEqual(set(h), set(rule["properties"]))
            self.assertIn(h["assessment"], rule["properties"]["assessment"]["enum"])

    def test_rejects_invented_source_citation(self):
        reason = (
            "The registry CASE-TB-018 lists SYN-SUBJ-018, but result RES-TB-018 "
            "lists SYN-SUBJ-999; another record RES-TB-777 supposedly resolves it."
        )
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response(reason=reason)))

    def test_rejects_fabricated_subject_reference(self):
        reason = (
            "The registry CASE-TB-018 lists SYN-SUBJ-018, but result RES-TB-018 "
            "lists SYN-SUBJ-999; evidence also identifies SYN-SUBJ-666."
        )
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response(reason=reason)))

    def test_rejects_missing_required_citation(self):
        reason = (
            "The registry CASE-TB-018 lists SYN-SUBJ-018, but a lab result lists "
            "SYN-SUBJ-999; the subject identity needs staff verification."
        )
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response(reason=reason)))

    def test_rejects_clinical_outcome_claim(self):
        reason = (
            "The registry CASE-TB-018 lists SYN-SUBJ-018, but result RES-TB-018 "
            "lists SYN-SUBJ-999; the patient missed treatment."
        )
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response(reason=reason)))

    def test_rejects_outreach_or_approval(self):
        question = "Should we contact the patient or auto approve this result?"
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response(question=question)))

    def test_rejects_invalid_json_and_extra_model_fields(self):
        for answer in (
            "No discrepancy",
            json.dumps({"explanations": [], "diagnosis": "TB"}),
            json.dumps({"explanations": [json.loads(sample_response())["explanations"][0],
                                             json.loads(sample_response())["explanations"][0]]}),
            sample_response(index=2),
        ):
            with self.subTest(answer=answer), self.assertRaises(CaseLensValidationError):
                describe_case(self.bundle, Stub(answer))

    def test_no_exception_is_not_false_claim_of_complete_care(self):
        self.bundle["exceptions"] = []
        stub = Stub("NEVER CALLED")
        report = describe_case(self.bundle, stub)
        self.assertEqual(report["hypotheses"], [])
        self.assertIn("incomplete source snapshots", report["unresolved_questions"][0])
        self.assertEqual(stub.calls, [])

    def test_rejects_non_synthetic_or_dangling_evidence(self):
        self.bundle["observations"][0]["subject_ref"] = "PATIENT-REAL-001"
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response()))
        self.bundle = json.loads(FIXTURE.read_text())
        self.bundle["exceptions"][0]["evidence_record_ids"] = ["RES-TB-NONEXISTENT"]
        with self.assertRaises(CaseLensValidationError):
            describe_case(self.bundle, Stub(sample_response()))

    def test_not_found_is_unresolved_not_proven_missed_service(self):
        self.bundle["exceptions"] = [{
            "category": "lab_document_not_found_in_query",
            "description": "The synthetic lab document was not returned.",
            "evidence_record_ids": ["ORD-TB-018"],
        }]
        reason = (
            "A lab order ORD-TB-018 is returned, while no matching lab result "
            "document is found in the bounded query. The complete source "
            "snapshot and any outside records remain unverified."
        )
        stub = Stub(sample_response(reason=reason, question=(
            "Can an authorized reviewer verify whether lab documentation for "
            "ORD-TB-018 exists in another permitted source?"
        )))
        report = describe_case(self.bundle, stub)
        self.assertEqual(report["hypotheses"][0]["assessment"], "unresolved")
        self.assertEqual(report["hypotheses"][0]["evidence_record_ids"], ["ORD-TB-018"])

    def test_cli_dry_run_does_not_use_nvidia_key(self):
        out = StringIO()
        with redirect_stdout(out):
            rc = main(["--case-id", "CASE-TB-018", "--bundle", str(FIXTURE), "--dry-run"])
        self.assertEqual(rc, 0)
        self.assertFalse(json.loads(out.getvalue())["nemotron_called"])


class NvidiaTransportTests(unittest.TestCase):
    def test_api_requires_key(self):
        client = NVIDIAChatClient(api_key="", timeout_seconds=30)
        with self.assertRaises(NemotronError):
            client.complete([{"role": "system", "content": "rule"},
                             {"role": "user", "content": "fake data"}])

    def test_request_is_nvidia_https_and_not_streamed(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, max_size): return json.dumps({
                "choices": [{"finish_reason": "stop",
                             "message": {"content": sample_response()}}]
            }).encode("utf-8")

        client = NVIDIAChatClient(api_key="FAKE-UNIT-TEST-KEY", timeout_seconds=30)
        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            got = client.complete([
                {"role": "system", "content": "reason about synthetic records"},
                {"role": "user", "content": "CASE-TB-018"},
            ])
        self.assertEqual(got, sample_response())
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://integrate.api.nvidia.com/v1/chat/completions")
        body = json.loads(request.data)
        self.assertEqual(body["stream"], False)
        self.assertEqual(body["model"], "nvidia/nemotron-3-super-120b-a12b")
        self.assertEqual(body["reasoning_effort"], "none")
        self.assertNotIn("FAKE-UNIT-TEST-KEY", json.dumps(body))

    def test_ultra_disables_thinking_for_bounded_json(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, max_size): return json.dumps({
                "choices": [{"finish_reason": "stop",
                             "message": {"content": sample_response()}}]
            }).encode("utf-8")

        client = NVIDIAChatClient(
            api_key="FAKE-UNIT-TEST-KEY",
            model="nvidia/nemotron-3-ultra-550b-a55b",
            timeout_seconds=30,
        )
        with patch("urllib.request.urlopen", return_value=Response()) as urlopen:
            result = client.complete([
                {"role": "system", "content": "Explain synthetic evidence"},
                {"role": "user", "content": "CASE-TB-018"},
            ])
        self.assertEqual(result, sample_response())
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://integrate.api.nvidia.com/v1/chat/completions")
        payload = json.loads(request.data)
        self.assertEqual(payload["model"], "nvidia/nemotron-3-ultra-550b-a55b")
        self.assertEqual(payload["reasoning_effort"], "none")
        self.assertIs(payload["stream"], False)

    def test_ultra_defaults_to_longer_timeout(self):
        ultra = NVIDIAChatClient(
            api_key="FAKE-UNIT-TEST-KEY",
            model="nvidia/nemotron-3-ultra-550b-a55b",
        )
        ordinary = NVIDIAChatClient(api_key="FAKE-UNIT-TEST-KEY")
        self.assertEqual(ultra.timeout_seconds, 180)
        self.assertEqual(ordinary.timeout_seconds, 75)
        self.assertEqual(NVIDIAChatClient(
            api_key="FAKE-UNIT-TEST-KEY",
            model="nvidia/nemotron-3-ultra-550b-a55b",
            timeout_seconds=30,
        ).timeout_seconds, 30)

    def test_transport_timeout_error_is_distinct_and_redacted(self):
        import urllib.error
        client = NVIDIAChatClient(
            api_key="SENSITIVE-FAKE-KEY",
            model="nvidia/nemotron-3-ultra-550b-a55b",
        )
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(
            TimeoutError("timed out")
        )) as urlopen:
            with self.assertRaisesRegex(NemotronError, "timed out.*180s") as ctx:
                client.complete([
                    {"role": "system", "content": "synthetic evidence only"},
                    {"role": "user", "content": "CASE-TB-018"},
                ])
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 180)
        self.assertNotIn("SENSITIVE-FAKE-KEY", str(ctx.exception))

    def test_transport_dns_error_is_distinct(self):
        import urllib.error
        client = NVIDIAChatClient(api_key="FAKE-UNIT-TEST-KEY")
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError(
            OSError("Name or service not known")
        )):
            with self.assertRaisesRegex(NemotronError, "network/DNS/TLS"):
                client.complete([
                    {"role": "system", "content": "rule"},
                    {"role": "user", "content": "fake data"},
                ])

    def test_wrong_response_shape_fails_closed(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, max_size): return b'{"results": []}'
        client = NVIDIAChatClient(api_key="FAKE-UNIT-TEST-KEY", timeout_seconds=30)
        with patch("urllib.request.urlopen", return_value=Response()):
            with self.assertRaises(NemotronError):
                client.complete([{"role": "system", "content": "rule"},
                                 {"role": "user", "content": "fake data"}])


if __name__ == "__main__":
    unittest.main()
