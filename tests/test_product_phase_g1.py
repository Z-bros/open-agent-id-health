"""TBCare Phase G.1 — truthful feedback and safe human-review statuses."""
from pathlib import Path
import re
import unittest

WEB = Path(__file__).resolve().parents[1] / "apps/product/web"
JS = (WEB / "app.js").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")
CSS = (WEB / "style.css").read_text(encoding="utf-8")


class TBCareInteractionSemanticsTests(unittest.TestCase):
    def test_brand_uses_human_facing_name_without_mutating_api(self):
        self.assertIn("<title>TBCare · Administrative Review</title>", HTML)
        self.assertIn("<b>TBCare</b>", HTML)
        self.assertIn("<footer>TBCare ·", HTML)
        self.assertNotIn("TB-CareOS", HTML)
        self.assertIn("X-TBCareOS-Evidence-SHA256", JS)

    def test_explicit_loading_buttons_are_live_not_fake_timers(self):
        self.assertIn('setAgentButtonPhase(kind,"requested")', JS)
        self.assertIn('state.agentStartedAt[kind]=Date.now()', JS)
        self.assertIn("Date.parse(e.occurred_at_utc)>=started", JS)
        self.assertIn("setAgentButtonPhase(kind,latest.state)", JS)
        self.assertIn('setAgentButtonPhase(kind,"accepted")', JS)
        self.assertIn('setAgentButtonPhase(kind,"rejected")', JS)
        self.assertIn('setAgentButtonPhase("explain","stale_evidence")', JS)
        self.assertIn('setAgentButtonPhase("plan","stale_evidence")', JS)
        for stage in ("requested", "retrieving_evidence",
                      "waiting_for_model", "validating"):
            self.assertIn(stage, JS)
        self.assertIn('button.setAttribute("aria-busy"', JS)
        self.assertIn("ACTIVE_BUTTON_PHASES.has(phase)", JS)
        self.assertIn('data-phase="idle"', HTML)
        self.assertIn("animation:tbcare-spin", CSS)
        self.assertIn("prefers-reduced-motion", CSS)
        self.assertNotIn("setTimeout(()=>setAgentButtonPhase(", JS)

    def test_validated_does_not_mean_case_resolved(self):
        for value in (
            "Explanation validated · Administrative review required",
            "Verification proposals validated · Not executed · Human review required",
            "No discrepancy flagged in this snapshot · Evidence not certified complete",
            "Both validated · review required",
            "Output validated · Review still required",
        ):
            self.assertIn(value, JS)
        self.assertIn('dataset.state=noFinding?"no_findings":"review_required"', JS)
        self.assertIn('.agent-status[data-state="review_required"]', CSS)
        self.assertIn('.activity-entry[data-needs-review="true"]', CSS)
        self.assertIn('state.workflow[kind]!=="running"', JS)
        self.assertNotIn('Accepted · Bounded agent output · Human review required', JS)
        self.assertNotIn("Both accepted", JS)
        self.assertNotIn("Case resolved", HTML + JS)

    def test_status_failure_retains_citation_guards_and_manual_retries(self):
        self.assertIn("renderAgentFailure(kind,error)", JS)
        self.assertIn('retry.addEventListener("click",()=>invokeAgent(kind))', JS)
        self.assertIn('if(error.code==="evidence_snapshot_changed")', JS)
        self.assertIn('state.workflow.evidence="stale"', JS)
        self.assertIn('state.workflow.reviewCount', JS)
        self.assertIn('state.evidence.evidence_snapshot_sha256', JS)
        self.assertNotIn(".innerHTML", JS)


if __name__ == "__main__":
    unittest.main()
