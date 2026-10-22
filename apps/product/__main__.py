"""TB-CareOS product phase A: localhost-only interactive administrative review app.

No official health integrations, patient contact, SQL mutations, or automatic
AI calls. This server is a development/demo tool for synthetic cases only.
Uses stdlib to avoid installing new dependencies during the hackathon.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

from apps.careflow.reconcile import reconcile_case
from apps.caselens.explain import _context, describe_case
from apps.nextstep.plan import plan_case
from shared.inference.nemotron import NVIDIAChatClient
from shared.zetaris.readonly import ZetarisHelperClient

ROOT = Path(__file__).resolve().parent
CASE_RE = re.compile(r"^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$")
CASE_IDS = tuple(f"CASE-TB-{i:03d}" for i in range(1, 37))
MODEL = "nvidia/nemotron-3.5-lightning-30b-a3b"
STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class ProductService:
    def __init__(self, *, helper: str | None, namespace: str = "TBCARE_OS",
                 fixture: Path | None = None, model: str = MODEL):
        if fixture is None and not helper:
            raise ValueError("Provide --helper or --fixture")
        if fixture is not None and helper:
            raise ValueError("--fixture and --helper are mutually exclusive")
        self.fixture = fixture
        self.helper = ZetarisHelperClient(helper) if helper else None
        self.namespace = namespace
        self.model = model

    def list_cases(self) -> dict:
        """Advertise known synthetic IDs, NOT source availability/triage status."""
        ids = ("CASE-TB-018",) if self.fixture else CASE_IDS
        return {
            "cases": [{"case_id": item, "evidence_status": "not_checked"} for item in ids],
            "source_mode": "saved_fixture" if self.fixture else "live_zetaris",
            "requires_human_approval": True,
            "note": "Case list is synthetic ID inventory; no source coverage or clinical state was inferred.",
        }

    def evidence(self, case_id: str) -> dict:
        if not CASE_RE.fullmatch(case_id):
            raise ValueError("Only indexed fabricated CASE-TB-001 through CASE-TB-036 permitted")
        if self.fixture:
            if case_id != "CASE-TB-018":
                raise ValueError("Saved fixture mode only supports CASE-TB-018")
            b = json.loads(self.fixture.read_text(encoding="utf-8"))
        else:
            b = reconcile_case(self.helper, namespace=self.namespace, case_id=case_id)
        if not isinstance(b, dict) or b.get("case_id") != case_id:
            raise ValueError("Source evidence case mismatch")
        _context(b)
        return b

    def explain(self, case_id: str) -> dict:
        evidence = self.evidence(case_id)
        return describe_case(evidence, NVIDIAChatClient(model=self.model))

    def plan(self, case_id: str) -> dict:
        evidence = self.evidence(case_id)
        return plan_case(evidence, model_client=NVIDIAChatClient(model=self.model))


def make_handler(service: ProductService):
    class Handler(BaseHTTPRequestHandler):
        server_version = "TB-CareOSLocal/0.1"

        def _respond(self, status: int, value: dict):
            body = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.end_headers()
            self.wfile.write(body)

        def _safe_action(self, action):
            try:
                self._respond(200, action())
            except (ValueError, TypeError, KeyError, RuntimeError, OSError,
                    json.JSONDecodeError) as exc:
                # Provider/source exceptions may contain sensitive payloads.
                # Surface a generic failure, not raw token-bearing logs.
                self._respond(422, {
                    "error": "The request failed validation or an external source/model call failed.",
                    "error_type": type(exc).__name__,
                    "next_step": "Inspect local server diagnostics privately; do not interpret source failure as missing care.",
                })

        def do_GET(self):
            path = urlsplit(self.path).path
            if path in STATIC:
                file_name, media_type = STATIC[path]
                content = (ROOT / "web" / file_name).read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", media_type)
                self.send_header("Content-Length", str(len(content)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Content-Security-Policy",
                                 "default-src 'self'; script-src 'self'; style-src 'self'; "
                                 "connect-src 'self'; img-src 'none'; base-uri 'none'; "
                                 "form-action 'none'; frame-ancestors 'none'")
                self.end_headers()
                self.wfile.write(content)
                return
            if path == "/api/cases":
                self._respond(200, service.list_cases())
                return
            match = re.fullmatch(r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/evidence", path)
            if match:
                self._safe_action(lambda: service.evidence(match.group(1)))
                return
            self._respond(404, {"error": "Unknown API route"})

        def do_POST(self):
            path = urlsplit(self.path).path
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            # Browser pages are served by this same app. Disallow cross-site
            # request forgery and cross-origin browser model invocations.
            allowed_origin = f"http://{host}"
            if origin and origin != allowed_origin:
                self._respond(403, {"error": "Cross-origin request rejected"})
                return
            if self.headers.get("Content-Length", "0") != "0":
                self._respond(400, {"error": "This endpoint accepts no request body"})
                return
            match = re.fullmatch(r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/(explain|plan)", path)
            if not match:
                self._respond(404, {"error": "Unknown API action"})
                return
            case_id, method = match.groups()
            if not CASE_RE.fullmatch(case_id):
                self._respond(400, {"error": "Only the synthetic 36-case ID list is allowed"})
                return
            self._safe_action(lambda: service.explain(case_id) if method == "explain"
                              else service.plan(case_id))

        def do_PUT(self):
            self._respond(405, {"error": "No source mutations or clinical writes permitted"})

        do_PATCH = do_PUT
        do_DELETE = do_PUT

        def log_message(self, fmt, *args):
            # Avoid writing query strings, headers or credentials to logs.
            pass

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--helper", default=None,
                      help="Trusted official Zetaris query_zetaris.py path")
    mode.add_argument("--fixture", type=Path,
                      help="One saved synthetic bundle for offline UI demo")
    parser.add_argument("--namespace", default="TBCARE_OS")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--model", default=os.getenv("NEMOTRON_MODEL", MODEL))
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be 1024–65535")
    service = ProductService(
        helper=args.helper, namespace=args.namespace,
        fixture=args.fixture, model=args.model
    )
    host = "127.0.0.1"
    server = ThreadingHTTPServer((host, args.port), make_handler(service))
    print(f"TB-CareOS local app: http://{host}:{args.port}/", flush=True)
    print("Synthetic administrative evidence only. Ctrl+C stops the local app.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
