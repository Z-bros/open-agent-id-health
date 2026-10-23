"""Local append-only notes for explicit, fabricated administrative human reviews.

A note is NOT a signed approval, medical action, or Zetaris update. The only
permitted cases and cited IDs come from the revalidated evidence snapshot.
"""
from __future__ import annotations

from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from threading import RLock
import uuid
from typing import Any

from apps.caselens.explain import _context, _is_safe_string, _verify_refs

CASE_PATTERN = re.compile(r"^CASE-TB-(?:00[1-9]|0[12][0-9]|03[0-6])$")
LABEL_PATTERN = re.compile(r"^DEMO-[A-Z0-9_-]{2,24}$")
DISPOSITIONS = frozenset((
    "request_source_verification",
    "escalate_admin_review",
    "reviewed_unresolved",
))
MAX_LOG_BYTES = 2_000_000
MAX_ENTRIES = 500
SAFE_ID = re.compile(r"^[0-9a-f]{64}$")
FORBIDDEN_NOTE = re.compile(
    r"(?i)(?:https?://|www\.|@|[<>]|ground_truth|SITB|SATUSEHAT|"
    r"\b(?:send|contact|email|sms)\s+(?:the\s+)?patient\b|"
    r"\b(?:diagnos(?:is|e|ed)|prescri(?:be|ption|bed))\b|"
    r"\b(?:missed|completed|received)\s+(?:care|treatment)\b)"
)


class ReviewValidationError(ValueError):
    """Untrusted human note/input violates the local-only review contract."""


class ReviewConflictError(RuntimeError):
    """The evidence snapshot has changed or the request ID was reused."""


def snapshot_digest(bundle: dict[str, Any]) -> str:
    """Hash canonical synthetic evidence; no oracle labels or AI predictions."""
    _context(bundle)
    encoded = json.dumps(
        bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _check_request(bundle: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(draft, dict) or set(draft) != {
        "finding_index", "finding_category", "evidence_record_ids",
        "evidence_snapshot_sha256", "reviewer_label", "disposition",
        "note", "request_id",
    }:
        raise ReviewValidationError("Review input does not match allowlisted fields")
    index = draft["finding_index"]
    findings = bundle["exceptions"]
    if type(index) is not int or not 0 <= index < len(findings):
        raise ReviewValidationError("Review must target an existing CareFlow finding")
    issue = findings[index]
    if draft["finding_category"] != issue["category"] or (
        draft["evidence_record_ids"] != issue["evidence_record_ids"]
    ):
        raise ReviewValidationError("Review citation/category does not match retrieved finding")
    digest = snapshot_digest(bundle)
    supplied = draft["evidence_snapshot_sha256"]
    if not isinstance(supplied, str) or not SAFE_ID.fullmatch(supplied):
        raise ReviewValidationError("Invalid evidence snapshot ID")
    if digest != supplied:
        raise ReviewConflictError("Evidence snapshot changed: refresh before recording a review")

    who = draft["reviewer_label"]
    if not isinstance(who, str) or not LABEL_PATTERN.fullmatch(who):
        raise ReviewValidationError("Use a DEMO-* fictional reviewer label (4–29 characters)")
    if draft["disposition"] not in DISPOSITIONS:
        raise ReviewValidationError("Only non-clinical administrative dispositions are permitted")

    note = draft["note"]
    if not isinstance(note, str) or not 12 <= len(note.strip()) <= 280 or (
        "\n" in note or "\r" in note or FORBIDDEN_NOTE.search(note)
    ):
        raise ReviewValidationError("Use a 12–280-character synthetic administrative note")
    note = note.strip()
    _, _, allowed_records, allowed_subjects = _context(bundle)
    _verify_refs(note, allowed_records=allowed_records, allowed_subjects=allowed_subjects)
    if not _is_safe_string(note, 12, 280):
        raise ReviewValidationError("Note contains disallowed clinical or outreach content")
    identifier = draft["request_id"]
    if not isinstance(identifier, str):
        raise ReviewValidationError("Missing one-time request ID")
    try:
        parsed = uuid.UUID(identifier)
    except (ValueError, AttributeError) as exc:
        raise ReviewValidationError("Invalid one-time request ID") from exc
    if parsed.version != 4 or str(parsed) != identifier:
        raise ReviewValidationError("Request ID must be a canonical UUID v4")

    return {**draft, "note": note}


def _validated_records(case_id: str, data: bytes) -> list[dict[str, Any]]:
    if len(data) > MAX_LOG_BYTES:
        raise ReviewValidationError("Local review log exceeds bounded size")
    if not data:
        return []
    if not data.endswith(b"\n"):
        raise ReviewValidationError("Incomplete local review log; fail closed")
    out: list[dict[str, Any]] = []
    for line in data.splitlines():
        try:
            event = json.loads(line)
        except (ValueError, TypeError) as exc:
            raise ReviewValidationError("Invalid local review log; fail closed") from exc
        if not isinstance(event, dict) or set(event) != {
            "schema_version", "kind", "case_id", "review_event_id", "request_id",
            "recorded_at_utc", "finding_index", "finding_category",
            "evidence_record_ids", "evidence_snapshot_sha256",
            "reviewer_label", "disposition", "note",
            "official_action_taken", "human_identity_verified",
        } or event.get("schema_version") != "1.0.0" or (
            event.get("kind") != "human_administrative_note"
        ) or event.get("case_id") != case_id or (
            event.get("official_action_taken") is not False
        ) or event.get("human_identity_verified") is not False:
            raise ReviewValidationError("Invalid persisted review event")
        out.append(event)
        if len(out) > MAX_ENTRIES:
            raise ReviewValidationError("Too many persisted review events")
    if len({r["request_id"] for r in out}) != len(out):
        raise ReviewValidationError("Duplicated request ID in review history")
    return out


class ReviewStore:
    """Local file append with inter-thread/process locking; no Zetaris writes."""

    def __init__(self, directory: str | Path = "outputs/reviews"):
        self.directory = Path(directory).expanduser().resolve()
        self._lock = RLock()

    def _path(self, case_id: str) -> Path:
        if not CASE_PATTERN.fullmatch(case_id):
            raise ReviewValidationError("Only fabricated indexed case IDs are permitted")
        return self.directory / (case_id.lower() + ".jsonl")

    def history(self, case_id: str) -> list[dict[str, Any]]:
        path = self._path(case_id)
        with self._lock:
            if not path.exists():
                return []
            if path.is_symlink() or not path.is_file():
                raise ReviewValidationError("Review log is not an ordinary local file")
            if path.stat().st_size > MAX_LOG_BYTES:
                raise ReviewValidationError("Review log size exceeds limit")
            return _validated_records(case_id, path.read_bytes())

    def activity(self) -> list[dict[str, Any]]:
        """Only locally recorded cases; no inference of unchecked-case status."""
        summaries: list[dict[str, Any]] = []
        for i in range(1, 37):
            case_id = f"CASE-TB-{i:03d}"
            records = self.history(case_id)
            if records:
                last = records[-1]
                summaries.append({
                    "case_id": case_id,
                    "recorded_notes": len(records),
                    "latest_disposition": last["disposition"],
                    "last_recorded_at_utc": last["recorded_at_utc"],
                    "note": "Local notes only; not official case status.",
                })
        return summaries

    def record(self, bundle: dict[str, Any], draft: dict[str, Any]) -> dict[str, Any]:
        checked = _check_request(bundle, draft)
        case_id = bundle["case_id"]
        path = self._path(case_id)
        with self._lock:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.directory.is_symlink():
                raise ReviewValidationError("Symlinked review directory is not allowed")
            flags = os.O_RDWR | os.O_APPEND | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(path, flags, 0o600)
            try:
                fcntl.flock(fd, fcntl.LOCK_EX)
                os.fchmod(fd, 0o600)
                if not stat.S_ISREG(os.fstat(fd).st_mode):
                    raise ReviewValidationError("Review log must be a regular file")
                file_size = os.fstat(fd).st_size
                if file_size > MAX_LOG_BYTES:
                    raise ReviewValidationError("Review log size exceeds limit")
                os.lseek(fd, 0, os.SEEK_SET)
                previous = _validated_records(case_id, os.read(fd, file_size))
                for old in previous:
                    if old["request_id"] == checked["request_id"]:
                        fields = {key: old[key] for key in checked}
                        if fields != checked:
                            raise ReviewConflictError("Request ID reused for a different review")
                        return old
                if len(previous) >= MAX_ENTRIES:
                    raise ReviewValidationError("Review log entry limit reached")
                event = {
                    "schema_version": "1.0.0",
                    "kind": "human_administrative_note",
                    "case_id": case_id,
                    "review_event_id": "rev_" + str(uuid.uuid4()),
                    "request_id": checked["request_id"],
                    "recorded_at_utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
                    **checked,
                    "official_action_taken": False,
                    "human_identity_verified": False,
                }
                raw = (json.dumps(event, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
                if file_size + len(raw) > MAX_LOG_BYTES:
                    raise ReviewValidationError("Review log size limit reached")
                os.write(fd, raw)
                os.fsync(fd)
                return event
            finally:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
