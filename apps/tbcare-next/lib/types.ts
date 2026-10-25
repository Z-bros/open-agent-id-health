export type SourceStatus = "available" | "not_found" | "temporarily_unavailable" | "permission_denied" | "error" | "not_checked";
export type SourceCheck = { source_system: string; status: SourceStatus | string; attempt: number };
export type Observation = {
  record_id: string;
  source_system: string;
  source_record_id: string;
  subject_ref: string;
  record_type: string;
  observed_at: string;
  details: Record<string, unknown>;
};
export type Finding = { category: string; description: string; evidence_record_ids: string[] };
export type Evidence = {
  case_id: string;
  source_checks: SourceCheck[];
  observations: Observation[];
  exceptions: Finding[];
  evidence_snapshot_sha256: string;
  requires_human_approval: boolean;
};
export type ExplainResult = {
  hypotheses: { hypothesis: string; assessment: string; reason: string; evidence_record_ids: string[] }[];
  unresolved_questions: string[];
};
export type PlanResult = {
  actions: { action: string; source_system?: string; reason: string; evidence_record_ids?: string[] }[];
};
export type Review = {
  review_event_id: string;
  case_id: string;
  disposition: string;
  reviewer_label: string;
  finding_category: string;
  evidence_record_ids: string[];
  evidence_snapshot_sha256: string;
  recorded_at_utc: string;
  note: string;
};
export type Audit = {
  namespace?: string;
  has_persisted_events: boolean;
  event_count: number;
  audit_count: number;
  truncated: boolean;
  events: { event_id: string; event_type: string; event_at: string }[];
};
export type ApiFailure = { error: string; error_code: string; next_step?: string };
export type AgentPhase = "not_requested" | "running" | "accepted" | "rejected" | "no_findings";

// Actual local Python application activity — not the Meterless event index.
export type ServerActivityReport = {
  case_id: string;
  storage: "local_application_activity";
  total: number;
  background_worker_active: false;
  truncated: boolean;
  events: {
    event_id: string;
    run_id: string;
    case_id: string;
    operation: "careflow" | "caselens" | "nextstep" | "review";
    state: string;
    occurred_at_utc: string;
    error_code: string | null;
  }[];
};
