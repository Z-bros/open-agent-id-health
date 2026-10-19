"""Offline fabricated evidence for controlled tests."""
import json
from pathlib import Path
from .models import Case, Evidence

class SyntheticRepository:
    def __init__(self, path: str | Path):
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.cases = {
            obj["case_id"]: Case(obj["case_id"], obj["workflow"], obj["subject_ref"], tuple(obj["required_sources"]))
            for obj in data["cases"]
        }
        self.records = {(obj["case_id"], obj["source"]): Evidence(**obj) for obj in data["evidence"]}
        self.transient_failures = {
            (obj["case_id"], obj["source"]): int(obj["fail_count"])
            for obj in data.get("transient_failures", [])
        }
        self.calls: dict[tuple[str, str], int] = {}

    def fetch(self, case_id: str, source: str) -> Evidence | None:
        key = (case_id, source)
        self.calls[key] = self.calls.get(key, 0) + 1
        if self.calls[key] <= self.transient_failures.get(key, 0):
            return None
        return self.records.get(key)
