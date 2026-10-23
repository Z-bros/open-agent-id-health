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
from apps.caselens.explain import CaseLensValidationError, _context, describe_case
from apps.nextstep.plan import NextStepValidationError, plan_case
from apps.product.review_store import (ReviewStore, ReviewValidationError,
                                       ReviewConflictError, snapshot_digest)
from apps.product.audit_reader import MeterlessAuditReader, AuditReadError
from shared.inference.nemotron import NVIDIAChatClient, NemotronError
from shared.zetaris.readonly import ZetarisHelperClient, ZetarisQueryError

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
                 fixture: Path | None = None, model: str = MODEL,
                 review_dir: str | Path = "outputs/reviews",
                 meterless_reference: str | Path | None = None,
                 meterless_state_dir: str | Path = "outputs/meterless"):
        if fixture is None and not helper:
            raise ValueError("Provide --helper or --fixture")
        if fixture is not None and helper:
            raise ValueError("--fixture and --helper are mutually exclusive")
        self.fixture = fixture
        self.helper = ZetarisHelperClient(helper) if helper else None
        self.namespace = namespace
        self.model = model
        self.reviews_store = ReviewStore(review_dir)
        self.audit_reader = MeterlessAuditReader(
            meterless_reference or Path.home() / "Meterless/engines/world-model/reference",
            meterless_state_dir,
        )

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

    def evidence_response(self, case_id: str) -> dict:
        bundle = self.evidence(case_id)
        return {**bundle, "evidence_snapshot_sha256": snapshot_digest(bundle)}

    def meterless_audit(self, case_id: str) -> dict:
        if not isinstance(case_id, str) or not CASE_RE.fullmatch(case_id):
            raise ValueError("Only indexed fabricated CASE-TB-001–036 audit IDs are allowed")
        return self.audit_reader.read(case_id)

    def review_history(self, case_id: str) -> dict:
        return {
            "case_id": case_id,
            "reviews": self.reviews_store.history(case_id),
            "identity_verified": False,
            "official_action_taken": False,
        }

    def review_activity(self) -> dict:
        return {
            "activity": self.reviews_store.activity(),
            "note": "Only cases with locally recorded notes. Unchecked cases are not inferred to be reviewed or cleared.",
        }

    def record_review(self, case_id: str, draft: dict) -> dict:
        # Reconcile source again before persisting; the UI-provided snapshot
        # must still match. No client claims are treated as source evidence.
        bundle = self.evidence(case_id)
        return self.reviews_store.record(bundle, draft)


def public_failure(exc: Exception) -> tuple[int, str, str, str]:
    """Safe, human-authored failure diagnostics only; never raw provider text."""
    if isinstance(exc, NemotronError):
        description = str(exc)
        if description.startswith("NVIDIA_API_KEY not set"):
            return (503, "nvidia_key_missing",
                    "NVIDIA_API_KEY is not available to this server process.",
                    "Set NVIDIA_API_KEY privately in the WSL shell launching the app, then restart the server.")
        match = re.search(r"NVIDIA API HTTP (\d{3})", description)
        if match:
            status = int(match.group(1))
            if status in (401, 403):
                return (503, "nvidia_access_denied",
                        f"NVIDIA rejected model access (HTTP {status}).",
                        "Check your key, model access, and NVIDIA Build credits.")
            if status == 404:
                return (503, "nvidia_model_unavailable",
                        "NVIDIA did not find the requested model (HTTP 404).",
                        "Confirm the exact model ID and availability in NVIDIA Build.")
            if status == 429:
                return (503, "nvidia_rate_limited",
                        "NVIDIA rate-limited the model request (HTTP 429).",
                        "Retry later or check the provider quota.")
            return (503, "nvidia_provider_error",
                    f"NVIDIA could not complete the request (HTTP {status}).",
                    "Check provider status, model access, and network availability.")
        if "timed out" in description:
            return (503, "nvidia_timeout",
                    "NVIDIA did not complete the request before its configured timeout.",
                    "Retry if provider latency improves.")
        if "connection failed" in description:
            return (503, "nvidia_network_error",
                    "The local server could not connect to NVIDIA.",
                    "Check network connectivity and DNS/TLS from WSL.")
        return (422, "nvidia_incomplete_response",
                "NVIDIA returned an empty, incomplete or unsupported model response.",
                "Try again. No unsupported output was accepted.")
    if isinstance(exc, AuditReadError):
        return (503, "meterless_audit_unavailable",
                "No readable validated Meterless event history is available for this case.",
                "Confirm Meterless reference installation, the local state directory, and prior E08 ingestion.")
    if isinstance(exc, ReviewConflictError):
        return (409, "review_conflict",
                "The evidence changed or a review request ID was reused.",
                "Refresh case evidence and review history before recording a new note.")
    if isinstance(exc, ReviewValidationError):
        return (422, "review_validation_rejected",
                "The review note, citation or disposition failed local validation.",
                "Use the selected finding, a fictional DEMO-* reviewer tag and a neutral administrative note.")
    if isinstance(exc, (CaseLensValidationError, NextStepValidationError)):
        return (422, "agent_validation_rejected",
                "The output failed evidence-grounding or bounded-action validation.",
                "Run the same case in the relevant CaseLens/NextStep CLI for a safe validator diagnostic.")
    if isinstance(exc, ZetarisQueryError):
        return (503, "zetaris_query_unavailable",
                "The read-only synthetic source query could not be completed.",
                "Check the local Zetaris service and query helper; do not infer missing care.")
    if isinstance(exc, (ValueError, TypeError, KeyError, json.JSONDecodeError)):
        return (422, "invalid_synthetic_evidence",
                "The evidence or request did not pass validation.",
                "Check the selected synthetic case and source availability.")
    return (500, "unexpected_internal_error",
            "The local application encountered an unexpected error.",
            "Inspect the local application setup without publishing secrets.")


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

        def _safe_action(self, action, *, success_status: int = 200):
            try:
                self._respond(success_status, action())
            except (ValueError, TypeError, KeyError, RuntimeError, OSError,
                    json.JSONDecodeError) as exc:
                status, code, message, next_step = public_failure(exc)
                self._respond(status, {
                    "error": message,
                    "error_code": code,
                    "next_step": next_step,
                })

        def _trusted_host(self) -> bool:
            # Binding loopback is insufficient against DNS rebinding if
            # Host is never checked. Deny other hostnames explicitly.
            port = self.server.server_address[1]
            return self.headers.get("Host", "") in (
                f"127.0.0.1:{port}", f"localhost:{port}"
            )

        def _review_body(self) -> dict:
            if self.headers.get("X-TBCareOS-Review-Intent") != "record-human-admin-review-v1":
                raise ReviewValidationError("Explicit review-intent header required")
            if self.headers.get("Content-Type", "").split(";")[0].strip().lower() != "application/json":
                raise ReviewValidationError("Review requires JSON content type")
            if self.headers.get("Transfer-Encoding"):
                raise ReviewValidationError("Chunked review bodies unsupported")
            value = self.headers.get("Content-Length", "")
            if not value.isdecimal() or not 1 <= int(value) <= 4096:
                raise ReviewValidationError("Review JSON request must be 1–4096 bytes")
            try:
                obj = json.loads(self.rfile.read(int(value)))
            except (ValueError, UnicodeError) as exc:
                raise ReviewValidationError("Invalid review request JSON") from exc
            if not isinstance(obj, dict):
                raise ReviewValidationError("Review request must be a JSON object")
            return obj

        def do_GET(self):
            if not self._trusted_host():
                self._respond(403, {"error": "Only localhost requests are permitted"})
                return
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
            if path == "/api/review-activity":
                self._safe_action(service.review_activity)
                return
            audit_match = re.fullmatch(
                r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/audit", path
            )
            if audit_match:
                self._safe_action(lambda: service.meterless_audit(audit_match.group(1)))
                return
            review_match = re.fullmatch(
                r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/reviews", path
            )
            if review_match:
                self._safe_action(lambda: service.review_history(review_match.group(1)))
                return
            match = re.fullmatch(r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/evidence", path)
            if match:
                self._safe_action(lambda: service.evidence_response(match.group(1)))
                return
            self._respond(404, {"error": "Unknown API route"})

        def do_POST(self):
            if not self._trusted_host():
                self._respond(403, {"error": "Only localhost requests are permitted"})
                return
            path = urlsplit(self.path).path
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            allowed_origin = f"http://{host}"
            if origin and origin != allowed_origin:
                self._respond(403, {"error": "Cross-origin request rejected"})
                return
            review_match = re.fullmatch(
                r"/api/cases/(CASE-TB-[A-Za-z0-9-]+)/reviews", path
            )
            if review_match:
                # A custom header requires a CORS preflight for cross-origin
                # JavaScript; this server never enables CORS.
                if origin != allowed_origin:
                    self._respond(403, {"error": "Review writes require the same-origin browser"})
                    return
                case_id = review_match.group(1)
                if not CASE_RE.fullmatch(case_id):
                    self._respond(400, {"error": "Only indexed fabricated cases permitted"})
                    return
                self._safe_action(
                    lambda: service.record_review(case_id, self._review_body()),
                    success_status=201,
                )
                return
            if self.headers.get("Content-Length", "0") != "0":
                self._respond(400, {"error": "This agent endpoint accepts no body"})
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
    parser.add_argument("--review-dir", type=Path, default=Path("outputs/reviews"),
                        help="Local append-only synthetic administrative review notes")
    parser.add_argument("--meterless-reference", type=Path,
                        default=Path.home() / "Meterless/engines/world-model/reference",
                        help="Local upstream Meterless World Model reference checkout")
    parser.add_argument("--meterless-state-dir", type=Path, default=Path("outputs/meterless"),
                        help="Local previously ingested Meterless state; audit GET never ingests")
    parser.add_argument("--model", default=os.getenv("NEMOTRON_MODEL", MODEL))
    args = parser.parse_args(argv)
    if not 1024 <= args.port <= 65535:
        parser.error("--port must be 1024–65535")
    service = ProductService(
        helper=args.helper, namespace=args.namespace,
        fixture=args.fixture, model=args.model,
        review_dir=args.review_dir,
        meterless_reference=args.meterless_reference,
        meterless_state_dir=args.meterless_state_dir,
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
