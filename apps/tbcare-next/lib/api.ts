import type { ApiFailure, Evidence, ExplainResult, PlanResult, Audit, Review, ServerActivityReport } from "./types";

// Optional local-only integration, never a public backend and never browser SQL.
const BASE = "/api/backend";
export const liveMode = process.env.NEXT_PUBLIC_TBCARE_MODE === "local";
export class RequestFailure extends Error {
  code: string;
  guidance: string;
  constructor(error: string, code: string, guidance = "") { super(error); this.code = code; this.guidance = guidance; }
}
async function request<T>(url: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(BASE + url, { cache: "no-store", ...init }); }
  catch { throw new RequestFailure("Local server connection failed", "local_api_unavailable", "Start the localhost Python server and verify proxy configuration."); }
  const value: (T & ApiFailure) | ApiFailure = await response.json().catch(() => ({ error: "Unreadable server response", error_code: "invalid_api_response" }));
  if (!response.ok) throw new RequestFailure(value.error ?? "Request failed", value.error_code ?? "request_failed", value.next_step ?? "");
  return value as T;
}
export const backendApi = {
  listCases: () => request<{cases: {case_id: string}[]; source_mode: string}>("/cases"),
  evidence: (id: string) => request<Evidence>(`/cases/${id}/evidence`),
  explain: (id: string, sha: string) => request<ExplainResult>(`/cases/${id}/explain`, { method: "POST", headers: { "X-TBCareOS-Evidence-SHA256": sha } }),
  plan: (id: string, sha: string) => request<PlanResult>(`/cases/${id}/plan`, { method: "POST", headers: { "X-TBCareOS-Evidence-SHA256": sha } }),
  reviews: (id: string) => request<{reviews: Review[]}>(`/cases/${id}/reviews`),
  audit: (id: string) => request<Audit>(`/cases/${id}/audit`),
  caseActivity: (id: string) => request<ServerActivityReport>(`/cases/${id}/activity`),
  activity: () => request<{activity: { case_id: string; recorded_notes: number }[]}>("/review-activity"),
  saveReview: (id: string, payload: Record<string, unknown>) => request<{review_event_id: string}>(`/cases/${id}/reviews`, { method: "POST", headers: { "Content-Type": "application/json", "X-TBCareOS-Review-Intent": "record-human-admin-review-v1" }, body: JSON.stringify(payload) }),
};
