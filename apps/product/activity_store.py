"""Truthful per-case agent activity events for the synthetic localhost product.

Activity is an *application* log, not Meterless, not a provider reasoning
trace, not a background worker, and not an authenticated reviewer log.
Only allowlisted state transitions supplied by application code are stored.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock
import uuid

_CASE = re.compile(r"^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$")
_ERROR = re.compile(r"^[a-z][a-z0-9_]{0,63}$")
_OPERATIONS = frozenset(("careflow", "caselens", "nextstep", "review"))
_STATES = frozenset((
    "requested", "retrieving_evidence", "waiting_for_model", "validating",
    "no_model_needed", "accepted", "rejected", "failed",
    "stale_evidence", "awaiting_human_review", "review_note_recorded",
))
_TERMINAL = frozenset((
    "accepted", "rejected", "failed", "stale_evidence", "review_note_recorded",
))
MAX_BYTES = 1_500_000
MAX_EVENTS = 1000
VISIBLE_EVENTS = 100


class ActivityLogError(RuntimeError):
    """Local activity history cannot be trusted or written."""


def _uuid(value: str) -> bool:
    try:
        return isinstance(value, str) and str(uuid.UUID(value)) == value
    except (ValueError, AttributeError, TypeError):
        return False


def _validate(case_id: str, obj: dict) -> None:
    if not isinstance(obj, dict) or set(obj) != {
        "schema_version", "event_id", "run_id", "case_id", "operation",
        "state", "occurred_at_utc", "error_code",
    } or obj["schema_version"] != "1.0.0" or obj["case_id"] != case_id or (
        not _uuid(obj["run_id"]) or not _uuid(obj["event_id"])
    ) or obj["operation"] not in _OPERATIONS or obj["state"] not in _STATES or (
        not isinstance(obj["occurred_at_utc"], str) or
        len(obj["occurred_at_utc"]) > 40 or not obj["occurred_at_utc"].endswith("+00:00")
    ) or (obj["error_code"] is not None and (
        not isinstance(obj["error_code"], str)
        or not _ERROR.fullmatch(obj["error_code"])
    )):
        raise ActivityLogError("Invalid activity event: fail closed")
    if obj["error_code"] is not None and obj["state"] not in ("rejected", "failed", "stale_evidence"):
        raise ActivityLogError("Error code is only valid for unsuccessful terminal state")
    if obj["operation"] == "review" and obj["state"] not in ("review_note_recorded",):
        raise ActivityLogError("A review activity can only represent a locally recorded note")


def _parse(case_id: str, payload: bytes) -> list[dict]:
    if len(payload) > MAX_BYTES or (payload and not payload.endswith(b"\n")):
        raise ActivityLogError("Activity file too large or incomplete")
    items: list[dict] = []
    for line in payload.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, UnicodeError) as exc:
            raise ActivityLogError("Corrupt activity file") from exc
        _validate(case_id, event)
        items.append(event)
        if len(items) > MAX_EVENTS:
            raise ActivityLogError("Activity event limit reached")
    if len({e["event_id"] for e in items}) != len(items):
        raise ActivityLogError("Duplicate persisted activity event ID")
    return items


class ActivityStore:
    def __init__(self, directory: str | Path = "outputs/activities"):
        self.directory = Path(directory).expanduser().resolve()
        self.lock = RLock()

    def _path(self, case_id: str) -> Path:
        if not isinstance(case_id, str) or not _CASE.fullmatch(case_id):
            raise ValueError("Only indexed fabricated case activity may be read")
        return self.directory / (case_id.lower() + ".jsonl")

    def history(self, case_id: str) -> dict:
        path = self._path(case_id)
        with self.lock:
            if not path.exists():
                items = []
            else:
                if path.is_symlink() or not path.is_file():
                    raise ActivityLogError("Activity must use ordinary local files")
                if path.stat().st_size > MAX_BYTES:
                    raise ActivityLogError("Activity file too large")
                items = _parse(case_id, path.read_bytes())
        return {
            "case_id": case_id, "storage": "local_application_activity",
            "background_worker_active": False,
            "total": len(items), "events": items[-VISIBLE_EVENTS:],
            "truncated": len(items) > VISIBLE_EVENTS,
            "note": "Server-observed application states only; not private model reasoning or Meterless events.",
        }

    def append(self, case_id: str, operation: str, state: str, *,
               run_id: str, error_code: str | None = None) -> dict:
        path = self._path(case_id)
        event = {
            "schema_version": "1.0.0",
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "case_id": case_id,
            "operation": operation, "state": state,
            "occurred_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "error_code": error_code,
        }
        _validate(case_id, event)
        with self.lock:
            self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
            if self.directory.is_symlink():
                raise ActivityLogError("Activity directory cannot be a symlink")
            fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_APPEND
                         | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ActivityLogError("Activity must be a normal file")
                os.fchmod(fd, 0o600)
                length = os.fstat(fd).st_size
                if length > MAX_BYTES:
                    raise ActivityLogError("Activity file exceeds cap")
                os.lseek(fd, 0, os.SEEK_SET)
                prior = _parse(case_id, os.read(fd, length))
                # The same review UUID must never create multiple local
                # "review note recorded" activity events on idempotent retry.
                if operation == "review" and any(
                    e["operation"] == "review" and e["run_id"] == run_id
                    for e in prior
                ):
                    return next(e for e in prior if
                                e["operation"] == "review" and e["run_id"] == run_id)
                if len(prior) >= MAX_EVENTS:
                    raise ActivityLogError("Activity event cap reached")
                raw = (json.dumps(event, sort_keys=True, separators=(",", ":"))
                       + "\n").encode("utf-8")
                if length + len(raw) > MAX_BYTES:
                    raise ActivityLogError("Activity file bytes limit reached")
                os.write(fd, raw)
                os.fsync(fd)
                return event
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
