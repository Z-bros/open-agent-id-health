"""Phase G: real localhost activity states, fail-closed logging, no fake worker."""
from contextlib import contextmanager
import http.client
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
from http.server import ThreadingHTTPServer
import unittest
from unittest.mock import patch
import uuid

from apps.product.activity_store import ActivityStore, ActivityLogError
from apps.product.__main__ import ProductService, make_handler

FIXTURE = Path(__file__).resolve().parent / "fixtures/tb_case_018_bundle.json"
WEB = Path(__file__).resolve().parents[1] / "apps/product/web"


@contextmanager
def serve(service):
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service)) as server:
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield server.server_address[1]
        finally:
            server.shutdown()
            thread.join(timeout=3)


def call(port, path, method="GET", headers=None, payload=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=8)
    raw = json.dumps(payload).encode() if payload is not None else None
    conn.request(method, path, body=raw, headers=headers or {})
    result = conn.getresponse()
    value = result.status, json.loads(result.read())
    conn.close()
    return value


class Model:
    def complete(self, messages):
        data = json.loads(messages[-1]["content"].split("\n", 1)[1])
        if "careflow_findings" in data:
            return json.dumps({"explanations":[{
                "finding_index":0,
                "reason":(
                    "Synthetic records CASE-TB-018 and RES-TB-018 contain "
                    "a subject-reference conflict between SYN-SUBJ-018 "
                    "and SYN-SUBJ-999 that requires staff verification."
                ),
                "unresolved_question":
                    "Which synthetic source record requires human verification?",
            }]})
        if "allowed_queries" in data:
            return json.dumps({"selected_query_ids":[data["allowed_queries"][0]["query_id"]]})
        raise AssertionError("Unexpected mock model input")


class ActivityStoreTests(unittest.TestCase):
    def test_state_log_persists_and_reopen_is_readonly(self):
        with TemporaryDirectory() as tmp:
            store = ActivityStore(tmp)
            case = "CASE-TB-018"
            run = str(uuid.uuid4())
            first = store.append(case,"caselens","requested",run_id=run)
            store.append(case,"caselens","waiting_for_model",run_id=run)
            store.append(case,"caselens","validating",run_id=run)
            store.append(case,"caselens","accepted",run_id=run)
            items = ActivityStore(tmp).history(case)
            self.assertEqual([e["state"] for e in items["events"]], [
                "requested", "waiting_for_model", "validating", "accepted",
            ])
            self.assertFalse(items["background_worker_active"])
            self.assertEqual(items["storage"], "local_application_activity")
            self.assertEqual(items["total"], 4)
            self.assertEqual(first["run_id"], run)
            self.assertEqual((Path(tmp)/"case-tb-018.jsonl").stat().st_mode & 0o777,0o600)
            self.assertEqual(ActivityStore(tmp).history("CASE-TB-009")["total"], 0)

    def test_review_idempotence_and_no_approval_states(self):
        with TemporaryDirectory() as tmp:
            store=ActivityStore(tmp)
            run=str(uuid.uuid4())
            a=store.append("CASE-TB-018","review","review_note_recorded",run_id=run)
            b=store.append("CASE-TB-018","review","review_note_recorded",run_id=run)
            self.assertEqual(a,b)
            self.assertEqual(store.history("CASE-TB-018")["total"],1)
            for operation, state in [
                ("review","accepted"), ("caselens","clinical_approval"),
                ("caselens","private_thinking"), ("bad_agent","accepted"),
            ]:
                with self.subTest(operation=operation,state=state):
                    with self.assertRaises(ActivityLogError):
                        store.append("CASE-TB-018",operation,state,run_id=str(uuid.uuid4()))

    def test_corrupt_file_fails_closed(self):
        with TemporaryDirectory() as tmp:
            f=Path(tmp)/"case-tb-018.jsonl"
            f.write_text('{"invalid":true}\n')
            store=ActivityStore(tmp)
            with self.assertRaises(ActivityLogError):
                store.history("CASE-TB-018")
            with self.assertRaises(ActivityLogError):
                store.append("CASE-TB-018","careflow","requested",run_id=str(uuid.uuid4()))
            self.assertEqual(f.read_text(),'{"invalid":true}\n')

    def test_strictly_bounded_fields_and_synthetic_case(self):
        with TemporaryDirectory() as tmp:
            store=ActivityStore(tmp)
            run=str(uuid.uuid4())
            for case in ("CASE-TB-999","../../real_person"):
                with self.assertRaises(ValueError):
                    store.history(case)
            with self.assertRaises(ActivityLogError):
                store.append("CASE-TB-018","careflow","failed",
                             run_id=run,error_code="private token: xyz")


class ActivityHTTPTests(unittest.TestCase):
    def service(self, tmp):
        return ProductService(helper=None,fixture=FIXTURE,review_dir=Path(tmp)/"reviews",
                              activity_dir=Path(tmp)/"activity")

    def test_source_get_logs_only_actual_received_steps(self):
        with TemporaryDirectory() as tmp:
            srv=self.service(tmp)
            with serve(srv) as port:
                status,evidence=call(port,"/api/cases/CASE-TB-018/evidence")
                self.assertEqual(status,200)
                status,history=call(port,"/api/cases/CASE-TB-018/activity")
                self.assertEqual(status,200)
                self.assertEqual([x["state"] for x in history["events"]],[
                    "requested","retrieving_evidence","accepted"
                ])
                self.assertEqual(history["total"],3)
                self.assertIn("evidence_snapshot_sha256",evidence)
                status,_=call(port,"/api/cases/CASE-TB-018/activity")
                self.assertEqual(status,200)
                self.assertEqual(srv.activity_history("CASE-TB-018")["total"],3)
                status,_=call(port,"/api/cases/CASE-TB-999/activity")
                self.assertEqual(status,422)

    def test_agent_real_checkpoint_model_validates_and_human_handoff(self):
        with TemporaryDirectory() as tmp:
            srv=self.service(tmp)
            with patch("apps.product.__main__.NVIDIAChatClient",return_value=Model()):
                with serve(srv) as port:
                    _,bundle=call(port,"/api/cases/CASE-TB-018/evidence")
                    status,result=call(
                        port,"/api/cases/CASE-TB-018/explain","POST",
                        {"X-TBCareOS-Evidence-SHA256":bundle["evidence_snapshot_sha256"]},
                    )
                    self.assertEqual(status,200,result)
                    history=srv.activity_history("CASE-TB-018")["events"]
                    sub=[x for x in history if x["operation"]=="caselens"]
                    self.assertEqual([x["state"] for x in sub],[
                        "requested","retrieving_evidence","waiting_for_model",
                        "validating","accepted","awaiting_human_review"
                    ])
                    self.assertEqual(len({x["run_id"] for x in sub}),1)
                    self.assertTrue(result["requires_human_approval"])

    def test_stale_evidence_is_visible_and_model_not_called(self):
        with TemporaryDirectory() as tmp:
            srv=self.service(tmp)
            with patch("apps.product.__main__.NVIDIAChatClient") as model:
                with serve(srv) as port:
                    status,result=call(port,"/api/cases/CASE-TB-018/explain",
                        "POST",{"X-TBCareOS-Evidence-SHA256":"0"*64})
                    self.assertEqual(status,409)
                    self.assertEqual(result["error_code"],"evidence_snapshot_changed")
                    statuses=[x for x in srv.activity_history("CASE-TB-018")["events"]
                              if x["operation"]=="caselens"]
                    self.assertEqual(statuses[-1]["state"],"stale_evidence")
                    self.assertEqual(statuses[-1]["error_code"],"evidence_snapshot_changed")
                model.assert_not_called()

    def test_rejected_model_does_not_become_accepted(self):
        with TemporaryDirectory() as tmp:
            srv=self.service(tmp)
            class InvalidModel:
                def complete(self,messages):
                    return '{"explanations":[{"unexpected":"unsafe"}]}'
            with patch("apps.product.__main__.NVIDIAChatClient",return_value=InvalidModel()):
                with serve(srv) as port:
                    _,bundle=call(port,"/api/cases/CASE-TB-018/evidence")
                    status,data=call(port,"/api/cases/CASE-TB-018/explain","POST",
                       {"X-TBCareOS-Evidence-SHA256":bundle["evidence_snapshot_sha256"]})
                    self.assertEqual(status,422)
                    self.assertEqual(data["error_code"],"caselens_unapproved_fields")
                    states=[x["state"] for x in srv.activity_history("CASE-TB-018")["events"]
                            if x["operation"]=="caselens"]
                    self.assertEqual(states[-1],"rejected")
                    self.assertNotIn("accepted",states)

    def test_saved_review_remains_saved_if_secondary_activity_log_fails(self):
        with TemporaryDirectory() as tmp:
            srv=self.service(tmp)
            bundle=srv.evidence_response("CASE-TB-018")
            issue=bundle["exceptions"][0]
            draft={
                "finding_index":0,
                "finding_category":issue["category"],
                "evidence_record_ids":issue["evidence_record_ids"],
                "evidence_snapshot_sha256":bundle["evidence_snapshot_sha256"],
                "reviewer_label":"DEMO-REVIEWER",
                "disposition":"reviewed_unresolved",
                "note":"Review the cited synthetic source discrepancy before any next step.",
                "request_id":str(uuid.uuid4()),
            }
            with patch.object(srv.activities,"append",
                              side_effect=ActivityLogError("activity unavailable")):
                saved=srv.record_review("CASE-TB-018",draft)
            self.assertEqual(saved["activity_log_status"],"unavailable")
            self.assertFalse(saved["official_action_taken"])
            self.assertEqual(len(srv.review_history("CASE-TB-018")["reviews"]),1)
            self.assertEqual(srv.activity_history("CASE-TB-018")["total"],0)

    def test_ui_only_polls_activity_no_background_worker_claims(self):
        js=(WEB/"app.js").read_text()
        html=(WEB/"index.html").read_text()
        self.assertIn('"/api/cases/"+encodeURIComponent(caseId)+"/activity"',js)
        self.assertIn('document.visibilityState==="visible"',js)
        self.assertIn('state.activitySeen',js)
        self.assertIn('No notification delivery occurs',html)
        self.assertIn('not the model',html.lower())
        self.assertNotIn(".innerHTML",js)


if __name__=="__main__":
    unittest.main()
