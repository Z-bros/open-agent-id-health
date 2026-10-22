"""E06 standalone read-only dashboard offline tests (synthetic fixture only)."""
from contextlib import redirect_stdout, redirect_stderr
from io import StringIO
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from apps.dashboard.__main__ import main
from apps.dashboard.render import render_dashboard
from apps.nextstep.plan import plan_case

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/tb_case_018_bundle.json"


def evidence():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def explanation():
    return {
        "schema_version": "1.0.0",
        "case_id": "CASE-TB-018",
        "hypotheses": [{
            "hypothesis": "Administrative review finding: subject_mismatch",
            "assessment": "supported",
            "reason": (
                "Case CASE-TB-018 cites SYN-SUBJ-018 but "
                "result RES-TB-018 cites SYN-SUBJ-999."
            ),
            "evidence_record_ids": ["CASE-TB-018", "RES-TB-018"],
        }],
        "unresolved_questions": [
            "Can staff verify which synthetic identifier is appropriate?"
        ],
        "requires_human_approval": True,
    }


def meterless_summary():
    return {
        "case_id": "CASE-TB-018",
        "world_model": "Meterless World Model reference",
        "replay": {"state_unchanged": True},
        "durable_state": {
            "event_count": 18,
            "observation_count": 6,
            "audit_count": 14,
        },
    }


class DashboardTests(unittest.TestCase):
    def test_full_dashboard_has_all_sections_and_correct_concerns(self):
        b = evidence()
        page = render_dashboard(
            b, explanation=explanation(),
            plan=plan_case(b), meterless_summary=meterless_summary(),
        )
        for fragment in (
            "<!doctype html>", "CASE-TB-018",
            'id="sources"', 'id="findings"', 'id="plan"',
            'id="timeline"', 'id="audit"',
            "CASE-TB-018", "RES-TB-018",
            "SYN-SUBJ-018", "SYN-SUBJ-999",
            "Proposed source check", "Human review required",
            "No real patient records", "Persisted observations",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, page)
        self.assertNotIn("<script", page.lower())
        self.assertIn("script-src &#39;none&#39;", page)
        self.assertIn("not executed", page)

    def test_html_escapes_untrusted_model_text_and_csp_blocks_network(self):
        b = evidence()
        injected = explanation()
        injected["hypotheses"][0]["reason"] += (
            '<img src=x onerror="alert(1)"> & saved explanation'
        )
        page = render_dashboard(b, explanation=injected)
        self.assertNotIn("<img", page)
        self.assertNotIn('onerror="alert(1)"', page)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", page)
        self.assertIn("connect-src &#39;none&#39;", page)
        self.assertIn("img-src &#39;none&#39;", page)
        self.assertNotIn("CaseLens explanation report supplied", page)

    def test_optional_reports_missing_are_explicit_not_inferred(self):
        page = render_dashboard(evidence())
        self.assertIn("No CaseLens explanation report supplied", page)
        self.assertIn("No NextStep plan supplied", page)
        self.assertIn("No Meterless run summary supplied", page)

    def test_rejects_cross_case_report_and_plan(self):
        b = evidence()
        altered = explanation()
        altered["case_id"] = "CASE-TB-777"
        with self.assertRaises(ValueError):
            render_dashboard(b, explanation=altered)
        p = plan_case(b)
        p["case_id"] = "CASE-TB-777"
        with self.assertRaises(ValueError):
            render_dashboard(b, plan=p)

    def test_rejects_unsupported_plan_action(self):
        b = evidence()
        p = plan_case(b)
        p["actions"][0]["action"] = "patient_message"
        with self.assertRaises(ValueError):
            render_dashboard(b, plan=p)

    def test_rejects_unsupported_subject_and_source_check(self):
        b = evidence()
        b["observations"][0]["subject_ref"] = "PATIENT-REAL-001"
        with self.assertRaises(ValueError):
            render_dashboard(b)
        b = evidence()
        b["source_checks"][0]["attempt"] = "not an integer"
        with self.assertRaises(ValueError):
            render_dashboard(b)

    def test_meterless_summary_requires_same_case_valid_replay(self):
        b = evidence()
        met = meterless_summary()
        met["case_id"] = "CASE-TB-777"
        with self.assertRaises(ValueError):
            render_dashboard(b, meterless_summary=met)
        met = meterless_summary()
        met["replay"]["state_unchanged"] = False
        with self.assertRaises(ValueError):
            render_dashboard(b, meterless_summary=met)

    def test_cli_writes_self_contained_html_without_provider(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "review.html"
            captured, err = StringIO(), StringIO()
            with redirect_stdout(captured), redirect_stderr(err):
                rc = main([
                    "--case-id", "CASE-TB-018",
                    "--bundle", str(FIXTURE),
                    "--output", str(out),
                ])
            self.assertEqual(rc, 0, err.getvalue())
            self.assertTrue(out.is_file())
            rendered = out.read_text(encoding="utf-8")
            self.assertIn("TB-CareOS", rendered)
            result = json.loads(captured.getvalue())
            self.assertFalse(result["explanation_included"])
            self.assertTrue(result["read_only"])
            self.assertTrue(result["requires_human_approval"])
            self.assertEqual(out.stat().st_mode & 0o777, 0o600)

    def test_cli_combined_saved_reports(self):
        with TemporaryDirectory() as tmp:
            tmpdir = Path(tmp)
            exp = tmpdir / "explanation.json"
            plan_file = tmpdir / "plan.json"
            met_file = tmpdir / "meterless.json"
            target = tmpdir / "full.html"
            exp.write_text(json.dumps(explanation()))
            plan_file.write_text(json.dumps(plan_case(evidence())))
            met_file.write_text(json.dumps(meterless_summary()))
            captured, err = StringIO(), StringIO()
            with redirect_stdout(captured), redirect_stderr(err):
                rc = main([
                    "--case-id", "CASE-TB-018",
                    "--bundle", str(FIXTURE),
                    "--explanation", str(exp),
                    "--plan", str(plan_file),
                    "--meterless-summary", str(met_file),
                    "--output", str(target),
                ])
            self.assertEqual(rc, 0, err.getvalue())
            result = json.loads(captured.getvalue())
            self.assertTrue(result["explanation_included"])
            self.assertTrue(result["plan_included"])
            self.assertTrue(result["meterless_summary_included"])
            self.assertIn("Persisted events", target.read_text())

    def test_cli_fail_closed_for_invalid_extension_and_mismatched_case(self):
        with TemporaryDirectory() as tmp:
            out = Path(tmp) / "review.txt"
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()) as err:
                code = main([
                    "--case-id", "CASE-TB-018", "--bundle", str(FIXTURE),
                    "--output", str(out),
                ])
            self.assertEqual(code, 2)
            self.assertFalse(out.exists())
            self.assertIn("failed closed", err.getvalue())
            with redirect_stdout(StringIO()), redirect_stderr(StringIO()):
                code = main([
                    "--case-id", "CASE-TB-777", "--bundle", str(FIXTURE),
                    "--output", str(Path(tmp) / "review.html"),
                ])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
