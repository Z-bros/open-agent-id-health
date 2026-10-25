import type { Evidence, ExplainResult, PlanResult, Observation, SourceStatus } from "./types";
export const demoIds = Array.from({ length: 36 }, (_, i) => `CASE-TB-${String(i + 1).padStart(3, "0")}`);
export const sourceNames = ["cases", "screening_events", "lab_orders", "lab_results", "followup_events"];
export const demoFixtures = ["CASE-TB-001", "CASE-TB-009", "CASE-TB-018"];

const observation = (record_id: string, record_type: string, source_record_id: string, subject_ref: string, date: string, details: Record<string, unknown> = {}): Observation => ({
  record_id, record_type, source_record_id, subject_ref, observed_at: date, details,
  source_system: record_type.toUpperCase() + "_SIM",
});
const demoDigest = (id: string) => (`demo-${id.toLowerCase()}-not-a-real-snapshot`);
const sourceChecks = (overrides: Record<string, SourceStatus> = {}) => sourceNames.map(source_system => ({
  source_system, attempt: 1, status: overrides[source_system] ?? "available",
}));
export const fixtureBundles: Record<string, Evidence> = {
  "CASE-TB-001": {
    case_id: "CASE-TB-001", requires_human_approval: true, evidence_snapshot_sha256: demoDigest("001"),
    source_checks: sourceChecks(), exceptions: [],
    observations: [
      observation("CASE-TB-001", "cases", "CASE-TB-001", "SYN-SUBJ-001", "2026-09-18T08:00:00Z", { source_table: "cases" }),
      observation("SCR-TB-001", "screening_events", "ROW-SCR-001", "SYN-SUBJ-001", "2026-09-18T09:00:00Z", { source_table: "screening_events" }),
      observation("ORD-TB-001", "lab_orders", "ROW-ORD-001", "SYN-SUBJ-001", "2026-09-18T10:00:00Z", { source_table: "lab_orders" }),
    ],
  },
  "CASE-TB-009": {
    case_id: "CASE-TB-009", requires_human_approval: true, evidence_snapshot_sha256: demoDigest("009"),
    source_checks: sourceChecks({ lab_results: "not_found" }),
    observations: [
      observation("CASE-TB-009", "cases", "CASE-TB-009", "SYN-SUBJ-009", "2026-09-18T08:00:00Z", { source_table: "cases" }),
      observation("SCR-TB-021", "screening_events", "ROW-SCR-021", "SYN-SUBJ-009", "2026-09-18T09:00:00Z", { source_table: "screening_events" }),
      observation("ORD-TB-009", "lab_orders", "ROW-ORD-009-A", "SYN-SUBJ-009", "2026-09-18T11:00:00Z", { source_table: "lab_orders", test: "GeneXpert" }),
    ],
    exceptions: [{ category: "missing_lab_document", description: "A related laboratory order is retrieved, but the current query returned no linked laboratory-result record. Source verification is required; this does not prove missed care.", evidence_record_ids: ["ORD-TB-009", "SCR-TB-021"] }],
  },
  "CASE-TB-018": {
    case_id: "CASE-TB-018", requires_human_approval: true, evidence_snapshot_sha256: demoDigest("018"),
    source_checks: sourceChecks({ followup_events: "not_found" }),
    observations: [
      observation("CASE-TB-018", "cases", "CASE-TB-018", "SYN-SUBJ-018", "2026-09-18T08:00:00Z", { source_table: "cases" }),
      observation("SCR-TB-044", "screening_events", "ROW-SCR-044", "SYN-SUBJ-018", "2026-09-18T09:30:00Z", { source_table: "screening_events" }),
      observation("ORD-TB-018", "lab_orders", "ROW-ORD-018-A", "SYN-SUBJ-018", "2026-09-18T11:00:00Z", { source_table: "lab_orders" }),
      observation("RES-TB-018", "lab_results", "ROW-RES-018-A", "SYN-SUBJ-999", "2026-09-19T11:00:00Z", { source_table: "lab_results", order_id: "ORD-TB-018" }),
    ],
    exceptions: [{ category: "subject_mismatch", description: "Retrieved case and laboratory-result records contain different synthetic subject references. Source linkage requires human verification.", evidence_record_ids: ["CASE-TB-018", "RES-TB-018"] }],
  },
};
// Fictional scenarios for standalone UI demonstration ONLY; not backend responses.
export function demoExplain(id: string): ExplainResult {
  if (id === "CASE-TB-001") return { hypotheses: [], unresolved_questions: [] };
  if (id === "CASE-TB-018") return {
    hypotheses: [{
      hypothesis: "subject_mismatch", assessment: "requires_human_review",
      reason: "Retrieved records CASE-TB-018 and RES-TB-018 show different synthetic subject references (SYN-SUBJ-018 and SYN-SUBJ-999). Their linkage must be checked by a human reviewer.",
      evidence_record_ids: ["CASE-TB-018", "RES-TB-018"],
    }],
    unresolved_questions: ["Do both records refer to the intended synthetic subject, or does the source linkage need correction?"],
  };
  throw { error_code: "caselens_unretrieved_citation", error: "Illustrative model response rejected: a referenced result was not retrieved.", next_step: "Inspect the retrieved order and explicitly retry if appropriate." };
}
export function demoPlan(id: string): PlanResult {
  const ref = id === "CASE-TB-009" ? ["ORD-TB-009", "SCR-TB-021"] : ["CASE-TB-018", "RES-TB-018"];
  const checks = id === "CASE-TB-001" ? [] : [{ action: "read_only_source_query", source_system: id === "CASE-TB-009" ? "lab_results" : "cases / lab_results", reason: id === "CASE-TB-009" ? "Proposed: check whether a linked result exists for retrieved order ORD-TB-009. No query is executed." : "Proposed: compare retrieved subject references in CASE-TB-018 and RES-TB-018. No query is executed.", evidence_record_ids: ref }];
  return { actions: [...checks,
    { action: "manual_review", reason: "Human administrative reviewer must inspect cited records and decide whether source verification is necessary.", evidence_record_ids: id === "CASE-TB-001" ? [] : ref },
    { action: "stop", reason: "Stop. No automated verification or source mutation is permitted.", evidence_record_ids: [] },
  ] };
}
