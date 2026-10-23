"""TBCare design refresh: the new UI is independent, navigable and safe."""
from pathlib import Path
from html.parser import HTMLParser
from tempfile import TemporaryDirectory
import unittest

from apps.product.__main__ import STATIC, ProductService, make_handler
from tests.test_product_phase_g import serve, call

ROOT=Path(__file__).resolve().parents[1]/"apps/product/web"


class Structure(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids=[]
        self.stylesheets=[]
        self.open_sections=[]
        self.activity_after_agent=False
        self.in_case_content=False
        self.last_section=""
        self.brand=[]
        self.invalid_start=False
    def handle_starttag(self,tag,attrs):
        data=dict(attrs)
        if data.get("id"):
            self.ids.append(data["id"])
        if tag=="link" and data.get("rel")=="stylesheet":
            self.stylesheets.append(data.get("href"))
        if tag=="div" and data.get("id")=="case-content":
            self.in_case_content=True
        if data.get("id")=="agent-investigation":
            self.last_section="agent"
        if data.get("id")=="activity-center":
            self.activity_after_agent=self.in_case_content and self.last_section=="agent"
        if tag=="form" and data.get("id")=="review-form":
            self.brand.append("review")
        if tag=="button" and data.get("id") in ("explain","plan"):
            if data.get("type")!="button":
                self.invalid_start=True


class DesignRefreshContractTests(unittest.TestCase):
    def test_distinct_brand_and_original_casework_controls(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        dom=Structure()
        dom.feed(html)
        self.assertTrue(dom.activity_after_agent)
        self.assertFalse(dom.invalid_start)
        self.assertEqual(dom.stylesheets,["/style.css","/theme.css"])
        for item in (
            "case-search","case-list","case-content","findings",
            "sources","timeline","review-form","review-history",
            "agent-investigation","explain","plan","activity-feed",
            "refresh","reload-audit","review-status","audit-status"
        ):
            self.assertEqual(dom.ids.count(item),1,item)
        self.assertIn("<b>TBCare</b>",html)
        self.assertIn("Administrative evidence review",html)
        self.assertNotIn("Kemenkes",html)
        self.assertNotIn("SATUSEHAT logo",html)
        self.assertIn("Synthetic records",html)

    def test_original_local_mode_and_read_only_routes_remain(self):
        self.assertEqual(STATIC["/theme.css"][0],"theme.css")
        self.assertTrue((ROOT/"theme.css").is_file())
        with TemporaryDirectory() as tmp:
            fixture=Path(__file__).parent/"fixtures/tb_case_018_bundle.json"
            service=ProductService(helper=None,fixture=fixture,
                                   review_dir=Path(tmp)/"reviews",
                                   activity_dir=Path(tmp)/"activity")
            with serve(service) as port:
                for route in ("/","/app.js","/style.css","/theme.css"):
                    status,_=call_raw(port,route)
                    self.assertEqual(status,200,route)
                status,data=call(port,"/api/cases/CASE-TB-018/evidence")
                self.assertEqual(status,200)
                self.assertTrue(data["evidence_snapshot_sha256"])
                status,events=call(port,"/api/cases/CASE-TB-018/activity")
                self.assertEqual(status,200)
                self.assertEqual(events["storage"],"local_application_activity")

    def test_visual_system_has_no_external_branding_or_ui_dependencies(self):
        css=(ROOT/"theme.css").read_text(encoding="utf-8")
        self.assertIn("--tbc-accent:#087875",css)
        self.assertIn(".sidebar{",css)
        self.assertIn(".metrics{",css)
        self.assertIn(".activity-center{",css)
        self.assertIn(".agent-status[data-state=\"review_required\"]",css)
        self.assertIn("@media(max-width:700px)",css)
        self.assertIn("prefers-reduced-motion",css)
        self.assertNotIn("@import",css)
        self.assertNotIn("url(",css)
        self.assertIn("Not a Kemenkes logo",css)


def call_raw(port,path):
    import http.client
    c=http.client.HTTPConnection("127.0.0.1",port,timeout=6)
    c.request("GET",path)
    resp=c.getresponse()
    value=resp.status,resp.read()
    c.close()
    return value


if __name__=="__main__":
    unittest.main()
