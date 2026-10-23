"""Phase D product UX contract: navigation, no invented case statuses, static safety.

These are DOM/asset contract checks; they do NOT substitute for manual browser
acceptance of visual layout, keyboard focus or actual live NVIDIA behavior.
"""
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import unittest

BASE = Path(__file__).resolve().parents[1] / "apps" / "product" / "web"
HTML = (BASE / "index.html").read_text(encoding="utf-8")
JS = (BASE / "app.js").read_text(encoding="utf-8")
CSS = (BASE / "style.css").read_text(encoding="utf-8")


class IdCollector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids = set()
        self.duplicates = set()
        self.demo_ids = []
        self.journey_targets = []
        self.buttons = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.duplicates.add(attrs["id"])
            self.ids.add(attrs["id"])
        if "data-demo-case" in attrs:
            self.demo_ids.append(attrs["data-demo-case"])
        if "data-journey-target" in attrs:
            self.journey_targets.append(attrs["data-journey-target"])
        if tag == "button":
            self.buttons.append(attrs)


class GuidedProductContracts(unittest.TestCase):
    def setUp(self):
        self.dom = IdCollector()
        self.dom.feed(HTML)

    def test_every_direct_element_lookup_exists_once(self):
        used = set(re.findall(r'\$\("([^"]+)"\)', JS))
        absent = sorted(used - self.dom.ids)
        self.assertFalse(absent, "Missing DOM element IDs: " + str(absent))
        self.assertEqual(self.dom.duplicates, set())

    def test_navigation_targets_and_real_scenario_ids(self):
        self.assertEqual(self.dom.demo_ids, [
            "CASE-TB-001", "CASE-TB-009", "CASE-TB-018"
        ])
        self.assertEqual(self.dom.journey_targets, [
            "findings-card", "agent-investigation",
            "review-panel", "meterless-audit"
        ])
        self.assertTrue(set(self.dom.journey_targets) <= self.dom.ids)
        self.assertIn("aria-live", HTML)
        self.assertIn("Skip to investigation", HTML)

    def test_every_scenario_is_an_opt_in_button(self):
        for attrs in self.dom.buttons:
            if "data-demo-case" in attrs:
                self.assertEqual(attrs.get("type"), "button")
        self.assertIn('state.ids.includes(btn.dataset.demoCase)', JS)
        self.assertIn('btn.disabled=!state.ids.includes(btn.dataset.demoCase)', JS)
        self.assertIn('renderList();', JS)

    def test_unvisited_cases_not_falsely_inferred_to_be_cleared(self):
        self.assertIn('state.inspected.get(id)', JS)
        self.assertIn('sources not checked in session', JS)
        self.assertIn('"Not checked"', JS)
        self.assertIn('state.localNotes.get(id)', JS)
        self.assertIn("not a case approval", HTML.lower())
        self.assertNotIn("automatically approve", HTML.lower())

    def test_agent_calls_remain_explicit_and_rejected_results_visible(self):
        beginning = JS.index("async function loadCase(id)")
        end = JS.index("function renderExplanation(", beginning)
        self.assertNotIn("invokeAgent(", JS[beginning:end])
        self.assertIn('addEventListener("click",()=>invokeAgent("explain"))', JS)
        self.assertIn('addEventListener("click",()=>invokeAgent("plan"))', JS)
        self.assertIn('state.workflow[kind==="explain"?"explain":"plan"]="rejected"', JS)
        self.assertIn('No substitute result was generated.', JS)
        self.assertIn("setLoad(true)", JS)
        self.assertIn('state.workflow.audit="unavailable"', JS)
        self.assertIn("No archived events", JS)
        self.assertIn('wf.reviewCount<0?"History unavailable"', JS)

    def test_readonly_safety_and_no_html_injection(self):
        self.assertNotIn(".innerHTML", JS)
        self.assertNotIn("document.write", JS)
        self.assertNotIn("eval(", JS)
        self.assertIn("textContent", JS)
        self.assertIn("no automatic actions", HTML.lower())
        self.assertIn("not yet archived in Meterless", HTML)

    @unittest.skipUnless(shutil.which("node"), "Node.js unavailable; browser syntax check deferred")
    def test_app_javascript_parses_in_node(self):
        result = subprocess.run(
            ["node", "--check", str(BASE / "app.js")],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
