"""TBCare dense workbench: textual status, keyboard routing and WCAG contrast."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]/"apps/product/web"
HTML=(ROOT/"index.html").read_text(encoding="utf-8")
CSS=(ROOT/"theme.css").read_text(encoding="utf-8")
JS=(ROOT/"app.js").read_text(encoding="utf-8")


def luminance(hex_rgb: str) -> float:
    rgb=[int(hex_rgb[i:i+2],16)/255 for i in (1,3,5)]
    channels=[c/12.92 if c <= 0.04045 else ((c+0.055)/1.055)**2.4 for c in rgb]
    return .2126*channels[0]+.7152*channels[1]+.0722*channels[2]


def contrast(foreground: str, background: str) -> float:
    hi,lo=sorted((luminance(foreground),luminance(background)),reverse=True)
    return (hi+.05)/(lo+.05)


class WorkbenchUxTests(unittest.TestCase):
    def test_semantic_label_contrast_meets_wcag_aa(self):
        for title, fg, bg in (
            ("primary action","#FFFFFF","#087875"),
            ("body ink","#1F3436","#FFFFFF"),
            ("secondary on white","#5A6C68","#FFFFFF"),
            ("secondary on canvas","#576B67","#F7F9F7"),
            ("verified source","#1F6157","#D8EFE5"),
            ("review required","#6B430B","#FDE4BA"),
            ("validation failure","#7B2E28","#FBE1DD"),
            ("read-only information","#204C59","#DDECF1"),
            ("neutral administrative state","#344F49","#EDF2EF"),
        ):
            with self.subTest(state=title):
                self.assertGreaterEqual(contrast(fg,bg),4.5)

    def test_status_never_equates_ai_acceptance_to_clinical_clearance(self):
        self.assertIn('id="case-status"',HTML)
        self.assertIn('data-state="not_checked"',HTML)
        self.assertIn("function renderCaseStatus()",JS)
        self.assertIn("Discrepancy · Review required",JS)
        self.assertIn("Discrepancy · Note recorded",JS)
        self.assertIn("No rule-based flags in checked records",JS)
        self.assertIn("Partial source access",JS)
        self.assertIn('status.dataset.state=code',JS)
        self.assertIn('.case-status[data-state="attention"]',CSS)
        self.assertIn('.case-status[data-state="failed"]',CSS)
        self.assertIn("--tbc-warn-bg:#FDE4BA",CSS)
        self.assertIn("--tbc-err-bg:#FBE1DD",CSS)
        self.assertNotIn("Care complete",JS + HTML)
        self.assertNotIn("Diagnosis confirmed",JS + HTML)

    def test_case_list_supports_native_click_and_arrow_key_selection(self):
        self.assertIn('role="group" aria-label="Synthetic case list"',HTML)
        self.assertIn('id="case-keyboard-help"',HTML)
        self.assertIn('["ArrowDown","ArrowUp","Home","End"]',JS)
        self.assertIn("choices[next].focus()",JS)
        self.assertIn('btn.addEventListener("click",() => loadCase(id))',JS)
        self.assertIn('btn.setAttribute("aria-controls","case-content")',JS)
        self.assertIn("event.preventDefault()",JS)
        self.assertIn(':focus-visible',CSS)
        self.assertIn('outline:3px solid #087875!important',CSS)
        self.assertIn('aria-live="polite"',HTML)
        self.assertIn('aria-busy="false"',HTML)

    def test_localized_literality_and_no_fake_clinical_or_fhir_data(self):
        for value in (
            "TB RECORD RECONCILIATION / CASE REVIEW",
            "Source verification",
            "Administrative discrepancies",
            "SIMULATED DATA — NOT FOR CLINICAL USE",
            "Missing digital evidence does not establish missed care",
            "SYNTHETIC · READ-ONLY",
        ):
            self.assertIn(value,HTML)
        for absent in ("Nomor IHS:", "FHIR connection success", "Blood type",
                       "SATUSEHAT integrated", "Kemenkes official"):
            self.assertNotIn(absent,HTML)
        self.assertIn('"Public Sans","Segoe UI"',CSS)
        self.assertNotIn("@import",CSS)
        self.assertNotIn("linear-gradient(",CSS)
        self.assertIn(".source-indicator{display:none}",CSS)
        self.assertIn(".source-row .chip{min-width:101px}",CSS)


if __name__=="__main__":
    unittest.main()
