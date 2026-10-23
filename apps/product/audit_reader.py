"""Read-only projection of local *real* Meterless event IDs, kinds and times.

Calls the separately installed upstream WorldModel.events()/audit() via tsx.
Does not invoke ingest or create any synthetic substitute audit history.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

_CASE = re.compile(r"^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$")
_EVENT = re.compile(r"^evt_[0-9]{1,12}$")
_KIND = re.compile(r"^[A-Za-z][A-Za-z0-9]{0,60}$")
MAX_BYTES = 250_000


class AuditReadError(RuntimeError):
    """Actual Meterless audit was unavailable or its output failed validation."""


class MeterlessAuditReader:
    def __init__(self, reference: str | Path, state_dir: str | Path):
        self.reference = Path(reference).expanduser().resolve()
        self.state_dir = Path(state_dir).expanduser().resolve()
        self.sidecar = Path(__file__).resolve().parents[2] / "scripts" / "meterless-audit-reader.mts"

    def read(self, case_id: str) -> dict:
        if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
            raise ValueError("Only synthetic indexed case IDs are permitted")
        tsx = self.reference / "node_modules" / ".bin" / "tsx"
        if not self.reference.joinpath("src/index.ts").is_file() or not tsx.is_file():
            raise AuditReadError("Upstream Meterless reference unavailable; run npm ci locally")
        if not self.state_dir.is_dir():
            raise AuditReadError("No previously persisted local Meterless audit directory")
        if not self.sidecar.is_file():
            raise AuditReadError("Local Meterless audit reader is missing")
        try:
            proc = subprocess.run(
                [
                    str(tsx), str(self.sidecar), "--reference", str(self.reference),
                    "--state-dir", str(self.state_dir), "--case-id", case_id,
                ],
                capture_output=True, text=True, encoding="utf-8",
                timeout=25, check=False, cwd=str(self.sidecar.parents[1]),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise AuditReadError("Meterless reader did not complete") from exc
        if proc.returncode != 0:
            raise AuditReadError("Meterless reader failed; inspect local upstream setup")
        if len(proc.stdout.encode("utf-8")) > MAX_BYTES:
            raise AuditReadError("Meterless audit response exceeds bounded size")
        try:
            obj = json.loads(proc.stdout)
        except (ValueError, TypeError) as exc:
            raise AuditReadError("Unrecognized Meterless audit response") from exc
        expected = {
            "schema_version", "kind", "case_id", "namespace", "store",
            "event_count", "audit_count", "has_persisted_events", "events",
            "truncated", "source", "timestamp_meaning",
        }
        if not isinstance(obj, dict) or set(obj) != expected or (
            obj["schema_version"] != "1.0.0"
            or obj["kind"] != "meterless_world_model_event_index"
            or obj["case_id"] != case_id
            or obj["namespace"] != "tbcareos_" + case_id.lower().replace("-", "_")
            or obj["store"] != "real_meterless_reference"
            or obj["source"] != "local_meterless_world_model"
            or obj["timestamp_meaning"] !=
                "Synthetic evidence snapshot/event time, not agent invocation or human-review time"
        ):
            raise AuditReadError("Meterless audit identity/source mismatch")
        events = obj["events"]
        if (
            type(obj["event_count"]) is not int or obj["event_count"] < 0
            or type(obj["audit_count"]) is not int or obj["audit_count"] < 0
            or type(obj["has_persisted_events"]) is not bool
            or obj["has_persisted_events"] != (obj["event_count"] > 0)
            or type(obj["truncated"]) is not bool
            or not isinstance(events, list) or len(events) > 200
            or len(events) > obj["event_count"]
            or obj["truncated"] != (obj["event_count"] > len(events))
        ):
            raise AuditReadError("Meterless audit counts invalid")
        for event in events:
            if not isinstance(event, dict) or set(event) != {
                "event_id", "event_type", "event_at",
            } or not isinstance(event["event_id"], str) or not _EVENT.fullmatch(event["event_id"]) or (
                not isinstance(event["event_type"], str) or not _KIND.fullmatch(event["event_type"])
            ) or (
                not isinstance(event["event_at"], str) or len(event["event_at"]) > 45
            ):
                raise AuditReadError("Meterless audit event invalid")
        return obj
