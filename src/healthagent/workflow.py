"""Deterministic retrieve–validate–retry–escalate loop (NOT an LLM agent)."""
from typing import Protocol
from .models import Case, Evidence, Finding, ReviewPackage

class EvidenceSource(Protocol):
    def fetch(self, case_id: str, source: str) -> Evidence | None: ...

class Investigator:
    def __init__(self, source: EvidenceSource, max_attempts: int = 2):
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        self.source = source
        self.max_attempts = max_attempts

    def run(self, case: Case) -> ReviewPackage:
        pkg = ReviewPackage(case_id=case.case_id, workflow=case.workflow, status="needs_human_review")
        pkg.trace.append({"step": "plan", "required_sources": list(case.required_sources)})
        for source_name in case.required_sources:
            record = None
            for attempt in range(1, self.max_attempts + 1):
                record = self.source.fetch(case.case_id, source_name)
                pkg.trace.append({"step": "retrieve", "source": source_name, "attempt": attempt,
                                  "outcome": "found" if record else "unavailable"})
                if record is not None:
                    break
                if attempt < self.max_attempts:
                    pkg.trace.append({"step": "retry", "source": source_name})
            if record is None:
                pkg.findings.append(Finding("missing_evidence", source_name,
                    "Record unavailable after bounded retries; verify manually."))
                continue
            pkg.evidence.append(record)
            if record.subject_ref != case.subject_ref:
                pkg.findings.append(Finding("subject_mismatch", source_name,
                    "Subject reference differs across records; verify manually."))
                pkg.trace.append({"step": "validate", "source": source_name, "outcome": "mismatch"})
            else:
                pkg.trace.append({"step": "validate", "source": source_name, "outcome": "matched"})
        pkg.status = "needs_human_review" if pkg.findings else "ready_for_review"
        pkg.trace.append({"step": "handoff", "status": pkg.status, "requires_approval": True})
        return pkg
