"""Intentionally minimal contracts; source identifiers are synthetic."""
from dataclasses import asdict, dataclass, field
from typing import Any

@dataclass(frozen=True)
class Case:
    case_id: str
    workflow: str
    subject_ref: str
    required_sources: tuple[str, ...]

@dataclass(frozen=True)
class Evidence:
    case_id: str
    source: str
    record_id: str
    subject_ref: str
    value: str

@dataclass(frozen=True)
class Finding:
    kind: str
    source: str
    reason: str

@dataclass
class ReviewPackage:
    case_id: str
    workflow: str
    status: str
    evidence: list[Evidence] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    requires_human_approval: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
