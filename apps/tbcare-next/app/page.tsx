"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import {
  Activity, AlertCircle, ArrowLeft, ArrowRight, BookOpen, Check, CheckCheck, CheckCircle2,
  ChevronDown, ChevronRight, CircleHelp, ClipboardCheck, ClipboardList, Clock3,
  Database, ExternalLink, FileClock, FileText, Filter, FolderOpen, HeartPulse,
  Info, Languages, Layers3, Link2, ListChecks, LoaderCircle, LockKeyhole,
  NotebookPen, PanelLeftClose, RefreshCw, Search, Settings2, ShieldCheck,
  Sparkles, Stethoscope, UserRoundCheck, XCircle
} from "lucide-react";
import type { ComponentType, ReactNode } from "react";
import { backendApi, liveMode, RequestFailure } from "@/lib/api";
import { demoExplain, demoFixtures, demoIds, fixtureBundles as fixtures, demoPlan, sourceNames } from "@/lib/demo";
import { translate, type Locale, type TextKey } from "@/lib/i18n";
import type { AgentPhase, Audit, Evidence, ExplainResult, Finding, PlanResult, Review, ServerActivityReport } from "@/lib/types";
import { ActivityToast, HumanCheckpoint, IntentStrip, NotificationCenter, ThinkingTrace, type ActivityNotice } from "@/app/components/AgentActivity";

type Screen = "explorer" | "investigation" | "activity" | "audit" | "settings";
type FilterMode = "all" | "not_checked" | "findings" | "notes";
type AgentUI<T> = { phase: AgentPhase; result?: T; error?: { code: string; message: string; guidance: string } };
const initialAgent = <T,>(): AgentUI<T> => ({ phase: "not_requested" });
const pad = (n: number) => String(n).padStart(2, "0");
function utcDate(s: string | undefined): string {
  if (!s) return "—";
  const d = new Date(s);
  if (Number.isNaN(d.valueOf())) return s;
  return `${d.getUTCFullYear()}-${pad(d.getUTCMonth() + 1)}-${pad(d.getUTCDate())} ${pad(d.getUTCHours())}:${pad(d.getUTCMinutes())} UTC`;
}
function pretty(s: string) { return s.replaceAll("_", " "); }
function humanError(error: unknown) {
  if (error instanceof RequestFailure) return { code: error.code, message: error.message, guidance: error.guidance };
  if (error && typeof error === "object" && "error_code" in error) {
    const e = error as { error_code: string; error?: string; next_step?: string };
    return { code: e.error_code, message: e.error ?? "Request rejected", guidance: e.next_step ?? "" };
  }
  return { code: "request_failed", message: error instanceof Error ? error.message : "Request failed", guidance: "" };
}
function Chip({ children, tone = "neutral", icon: Icon }: { children: ReactNode; tone?: "blue" | "green" | "amber" | "red" | "neutral" | "violet"; icon?: ComponentType<{ size?: number; strokeWidth?: number }> }) {
  return <span className={`chip chip-${tone}`}>{Icon && <Icon size={13} strokeWidth={2.4} />}{children}</span>;
}
function Card({ children, className = "", id }: { children: ReactNode; className?: string; id?: string }) {
  return <section id={id} className={`surface ${className}`}>{children}</section>;
}
function Head({ icon: Icon, title, desc, aside }: { icon: ComponentType<{ size?: number }>; title: string; desc?: string; aside?: ReactNode }) {
  return <div className="card-header"><div className="card-heading"><span className="head-icon"><Icon size={19} /></span><div><h3>{title}</h3>{desc && <p>{desc}</p>}</div></div>{aside && <div className="card-aside">{aside}</div>}</div>;
}
function Emphasis({ children }: { children: ReactNode }) { return <span className="mono-text">{children}</span>; }

export default function Page() {
  const [locale, setLocale] = useState<Locale>("id");
  const t = (key: TextKey) => translate(locale, key);
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  const [view, setView] = useState<Screen>("explorer");
  const [filter, setFilter] = useState<FilterMode>("all");
  const [search, setSearch] = useState("");
  const [ids, setIds] = useState<string[]>(demoIds);
  const [sourceMode, setSourceMode] = useState(liveMode ? "unknown" : "ui_fixture");
  const [backendConnection, setBackendConnection] = useState<"demo"|"checking"|"connected"|"unavailable">(liveMode ? "checking" : "demo");
  const [appError, setAppError] = useState("");
  const [selected, setSelected] = useState("CASE-TB-018");
  const [caseId, setCaseId] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence | null>(null);
  const [evidenceStatus, setEvidenceStatus] = useState<"not_checked" | "loading" | "loaded" | "failed" | "stale">("not_checked");
  const [inspected, setInspected] = useState<Record<string, { findings: number; observations: number; impaired: boolean; stale?: boolean }>>({});
  const [explain, setExplain] = useState<AgentUI<ExplainResult>>(initialAgent<ExplainResult>());
  const [plan, setPlan] = useState<AgentUI<PlanResult>>(initialAgent<PlanResult>());
  const [reviews, setReviews] = useState<Record<string, Review[]>>({});
  const [noteCounts, setNoteCounts] = useState<Record<string, number>>({});
  const [reviewIndex, setReviewIndex] = useState(0);
  const [disposition, setDisposition] = useState("request_source_verification");
  const [reviewNote, setReviewNote] = useState("");
  const [checked, setChecked] = useState(false);
  const [saveStatus, setSaveStatus] = useState("");
  const [saving, setSaving] = useState(false);
  const [audit, setAudit] = useState<Audit | null>(null);
  const [auditStatus, setAuditStatus] = useState<"not_checked" | "loading" | "available" | "empty" | "unavailable">("not_checked");
  const [auditError, setAuditError] = useState("");
  const [serverActivity, setServerActivity] = useState<ServerActivityReport | null>(null);
  const [flashRecord, setFlashRecord] = useState<string | null>(null);
  const [expandedRecords, setExpandedRecords] = useState<string[]>([]);
  const latest = useRef(0);
  const reviewRequestId = useRef<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [evidenceReviewed, setEvidenceReviewed] = useState(false);
  const [scopeAcknowledged, setScopeAcknowledged] = useState(false);
  const [notices, setNotices] = useState<ActivityNotice[]>([]);
  const [noticeOpen, setNoticeOpen] = useState(false);
  const [toastDismissed, setToastDismissed] = useState<string | null>(null);
  const [desktopNotify, setDesktopNotify] = useState(false);
  const [browserAvailable, setBrowserAvailable] = useState(false);
  useEffect(() => setBrowserAvailable(typeof window !== "undefined" && "Notification" in window), []);
  const desktopNotifyRef = useRef(false);
  const localeRef = useRef<Locale>("id");
  localeRef.current = locale;
  function pushNotice(titleKey: TextKey, tone: ActivityNotice["tone"], id?: string, detail?: string) {
    const entry: ActivityNotice = { id: crypto.randomUUID(), titleKey, tone, caseId: id, detail, at: Date.now(), read: false };
    setNotices(prev => [entry, ...prev].slice(0, 30));
    setToastDismissed(null);
    // Browser alerts are opt-in and only report completion of requests
    // initiated in this tab. No service worker / persistent job queue.
    if (desktopNotifyRef.current && typeof document !== "undefined" && document.hidden &&
        typeof Notification !== "undefined" && Notification.permission === "granted") {
      try { new Notification(`TBCare · ${translate(localeRef.current, titleKey)}`, { body: [id, detail].filter(Boolean).join(" · ") }); } catch { /* Browser may suppress notifications. */ }
    }
  }
  async function toggleDesktopNotifications() {
    if (desktopNotifyRef.current) {
      desktopNotifyRef.current = false;
      setDesktopNotify(false);
      return;
    }
    if (typeof window === "undefined" || !("Notification" in window)) {
      pushNotice("eventBrowserBlocked", "warning");
      return;
    }
    try {
      const permission = await Notification.requestPermission();
      if (permission !== "granted") { pushNotice("eventBrowserBlocked", "warning"); return; }
      desktopNotifyRef.current = true;
      setDesktopNotify(true);
      pushNotice("eventBrowserEnabled", "info");
    } catch { pushNotice("eventBrowserBlocked", "warning"); }
  }
  const mostRecentNotice = notices[0];
  useEffect(() => {
    if (!mostRecentNotice) return;
    const timeout = setTimeout(() => setToastDismissed(mostRecentNotice.id), 6800);
    return () => clearTimeout(timeout);
  }, [mostRecentNotice?.id]);


  useEffect(() => {
    if (!liveMode) return;
    let active = true;
    backendApi.listCases().then(data => {
      if (!active) return;
      setIds(data.cases.map(x => x.case_id));
      setSourceMode(data.source_mode);
      setBackendConnection("connected");
      setAppError("");
    }).catch(e => { if (active) { setBackendConnection("unavailable"); setAppError(humanError(e).message); } });
    backendApi.activity().then(data => {
      if (!active) return;
      const counts: Record<string, number> = {};
      data.activity.forEach(x => { counts[x.case_id] = x.recorded_notes; });
      setNoteCounts(counts);
    }).catch(() => {});
    return () => { active = false; };
  }, []);

  useEffect(() => {
    if (!liveMode || !caseId || view !== "investigation" || evidenceStatus !== "loaded") return;
    let active = true;
    const id = caseId;
    const refresh = async () => {
      if (document.visibilityState !== "visible") return;
      try {
        const response = await backendApi.caseActivity(id);
        if (active) setServerActivity(response);
      } catch {
        if (active) setServerActivity(null);
      }
    };
    void refresh();
    const interval = window.setInterval(() => void refresh(), 2000);
    return () => { active = false; window.clearInterval(interval); };
  }, [caseId, view, evidenceStatus]);

  async function retryBackendConnection() {
    if (!liveMode) return;
    setBackendConnection("checking");
    try {
      const data=await backendApi.listCases();
      setIds(data.cases.map(x=>x.case_id));
      setSourceMode(data.source_mode);
      setBackendConnection("connected");
      setAppError("");
      // A separate review-note endpoint can be unavailable without making
      // the case evidence API disconnected.
      try {
        const history=await backendApi.activity();
        const counts: Record<string,number>={};
        history.activity.forEach(x=>{counts[x.case_id]=x.recorded_notes;});
        setNoteCounts(counts);
      } catch { /* Note inventory unavailable; do not infer verified review. */ }
    } catch(error) {
      setBackendConnection("unavailable");
      setAppError(humanError(error).message);
    }
  }

  const rows = useMemo(() => ids.filter(id => {
    if (!id.toLowerCase().includes(search.trim().toLowerCase())) return false;
    if (filter === "not_checked") return !inspected[id];
    if (filter === "findings") return (inspected[id]?.findings ?? 0) > 0;
    if (filter === "notes") return (noteCounts[id] ?? 0) > 0;
    return true;
  }), [filter, ids, inspected, noteCounts, search]);
  const inspectedCount = ids.filter(id => !!inspected[id]).length;
  const findingsCount = Object.values(inspected).reduce((count, r) => count + r.findings, 0);
  const noteCaseCount = ids.filter(id => (noteCounts[id] ?? 0) > 0).length;
  const findingCaseCount = ids.filter(id => (inspected[id]?.findings ?? 0) > 0).length;
  const caseNotes = caseId ? (reviews[caseId] ?? []) : [];
  const hasFindings = !!evidence?.exceptions.length;
  const agentBusy = explain.phase === "running" || plan.phase === "running";
  const blocked = !evidence || evidenceStatus !== "loaded" || agentBusy || saving;
  const sourceSummary = evidence?.source_checks.some(s => !["available", "not_found"].includes(s.status)) ? t("partialSource") : t("sourceReadComplete");
  const formatStatus = (status: string) => {
    const labels: Record<string, TextKey> = { available: "available", not_found: "notFound", temporarily_unavailable: "temporarilyUnavailable", permission_denied: "permissionDenied", error: "error", not_checked: "notChecked" };
    return labels[status] ? t(labels[status]) : pretty(status);
  };
  const move = (next: Screen) => { setView(next); window.scrollTo({ top: 0, behavior: "smooth" }); };

  async function loadAudit(id: string, token: number) {
    setAudit(null);
    if (!liveMode) { setAuditStatus("empty"); return; }
    setAuditStatus("loading");
    try {
      const response = await backendApi.audit(id);
      if (token !== latest.current) return;
      setAudit(response);
      setAuditStatus(response.has_persisted_events ? "available" : "empty");
      if (response.has_persisted_events) pushNotice("eventAuditReady", "info", id, `${response.event_count} events`);
      setAuditError("");
    } catch (error) {
      if (token !== latest.current) return;
      setAuditStatus("unavailable");
      pushNotice("eventAuditUnavailable", "warning", id, humanError(error).code);
      setAuditError(humanError(error).code);
    }
  }

  async function loadCase(id: string) {
    if (!ids.includes(id) || (liveMode && backendConnection !== "connected")) return;
    if (agentBusy && caseId && id !== caseId) pushNotice("eventTrackingStopped", "warning", caseId);
    const token = ++latest.current;
    setSelected(id);
    setCaseId(id);
    setEvidence(null);
    setEvidenceStatus("loading");
    setExplain(initialAgent<ExplainResult>());
    setPlan(initialAgent<PlanResult>());
    setAudit(null);
    setServerActivity(null);
    setAuditStatus("not_checked");
    setSaveStatus("");
    setChecked(false);
    setReviewNote("");
    setReviewIndex(0);
    setExpandedRecords([]);
    setFlashRecord(null);
    setEvidenceReviewed(false);
    setScopeAcknowledged(false);
    reviewRequestId.current = null;
    move("investigation");
    try {
      const bundle = liveMode ? await backendApi.evidence(id) : fixtures[id];
      if (!bundle) throw new Error(t("unavailableFixture"));
      if (token !== latest.current) return;
      setEvidence(bundle);
      setEvidenceStatus("loaded");
      pushNotice("eventCaseRetrieved", "success", id, `${bundle.observations.length} records`);
      const impaired = bundle.source_checks.some(s => !["available", "not_found"].includes(s.status));
      setInspected(prev => ({ ...prev, [id]: { findings: bundle.exceptions.length, observations: bundle.observations.length, impaired } }));
      if (liveMode) {
        backendApi.reviews(id).then(data => {
          if (token !== latest.current) return;
          setReviews(prev => ({ ...prev, [id]: data.reviews }));
          setNoteCounts(prev => ({ ...prev, [id]: data.reviews.length }));
        }).catch(() => { if (token === latest.current) setSaveStatus("Local review history unavailable."); });
      }
      void loadAudit(id, token);
    } catch (error) {
      if (token !== latest.current) return;
      setEvidenceStatus("failed");
      pushNotice("eventCaseError", "error", id, humanError(error).code);
      setAppError(humanError(error).message);
    }
  }

  async function runAgent(kind: "explain" | "plan") {
    if (!caseId || !evidence || blocked) return;
    const id = caseId;
    const token = latest.current;
    if (kind === "explain") setExplain({ phase: "running" }); else setPlan({ phase: "running" });
    pushNotice(!evidence.exceptions.length ? "eventNoFindings" : kind === "explain" ? "eventExplainStarted" : "eventPlanStarted", "info", id);
    try {
      const result = liveMode
        ? kind === "explain" ? await backendApi.explain(id, evidence.evidence_snapshot_sha256) : await backendApi.plan(id, evidence.evidence_snapshot_sha256)
        : kind === "explain" ? demoExplain(id) : demoPlan(id);
      if (token !== latest.current) return;
      pushNotice(!evidence.exceptions.length ? "eventNoFindings" : kind === "explain" ? "eventExplainDone" : "eventPlanDone", evidence.exceptions.length ? "warning" : "info", id, liveMode ? undefined : "DEMO");
      if (kind === "explain") {
        const output = result as ExplainResult;
        setExplain({ phase: output.hypotheses.length ? "accepted" : "no_findings", result: output });
      } else setPlan({ phase: "accepted", result: result as PlanResult });
    } catch (error) {
      if (token !== latest.current) return;
      const detail = humanError(error);
      if (detail.code === "evidence_snapshot_changed") {
        setEvidenceStatus("stale");
        setInspected(prev => ({ ...prev, [id]: { ...(prev[id] ?? { findings: 0, observations: 0, impaired: false }), stale: true } }));
        setExplain(initialAgent<ExplainResult>());
        setPlan(initialAgent<PlanResult>());
        setAppError(t("snapshotStale"));
        pushNotice("eventStale", "warning", id, detail.code);
        return;
      }
      pushNotice(kind === "explain" ? "eventExplainRejected" : "eventPlanRejected", "error", id, detail.code);
      if (kind === "explain") setExplain({ phase: "rejected", error: detail });
      else setPlan({ phase: "rejected", error: detail });
    }
  }

  async function saveReview() {
    if (!caseId || !evidence || blocked || !hasFindings || !checked || !evidenceReviewed || !scopeAcknowledged || reviewNote.trim().length < 12 || reviewNote.trim().length > 280) return;
    const finding = evidence.exceptions[reviewIndex];
    if (!finding) return;
    if (!reviewRequestId.current) reviewRequestId.current = crypto.randomUUID();
    const token = latest.current;
    setSaving(true);
    setSaveStatus("");
    try {
      if (liveMode) {
        const data = await backendApi.saveReview(caseId, {
          finding_index: reviewIndex, finding_category: finding.category,
          evidence_record_ids: finding.evidence_record_ids,
          evidence_snapshot_sha256: evidence.evidence_snapshot_sha256,
          reviewer_label: "DEMO-REVIEWER", disposition,
          note: reviewNote.trim(), request_id: reviewRequestId.current,
        });
        if (token !== latest.current) return;
        const updated = await backendApi.reviews(caseId);
        setReviews(prev => ({ ...prev, [caseId]: updated.reviews }));
        setNoteCounts(prev => ({ ...prev, [caseId]: updated.reviews.length }));
        setSaveStatus(`${t("savedLocal")} (${data.review_event_id})`);
      } else {
        const syntheticReview: Review = {
          review_event_id: `DEMO-NOTE-${Date.now()}`, case_id: caseId, disposition, reviewer_label: "DEMO-REVIEWER",
          finding_category: finding.category, evidence_record_ids: finding.evidence_record_ids,
          evidence_snapshot_sha256: evidence.evidence_snapshot_sha256,
          recorded_at_utc: new Date().toISOString(), note: reviewNote.trim(),
        };
        setReviews(prev => ({ ...prev, [caseId]: [...(prev[caseId] ?? []), syntheticReview] }));
        setNoteCounts(prev => ({ ...prev, [caseId]: (prev[caseId] ?? 0) + 1 }));
        setSaveStatus(t("savedDemo"));
      }
      pushNotice("eventNoteSaved", "success", caseId, liveMode ? "LOCAL" : "DEMO · memory only");
      setChecked(false); setReviewNote(""); reviewRequestId.current = null;
    } catch (error) {
      const e = humanError(error);
      setSaveStatus(`${t("rejected")} [${e.code}]: ${e.message} ${e.guidance}`);
      pushNotice("eventNoteFailed", "error", caseId, e.code);
      if (e.code === "review_conflict") {
        setEvidenceStatus("stale");
        setExplain(initialAgent<ExplainResult>()); setPlan(initialAgent<PlanResult>());
      }
    } finally { if (token === latest.current) setSaving(false); }
  }

  function scrollToCitation(ref: string) {
    if (!evidence?.observations.some(record => record.record_id === ref)) return;
    setFlashRecord(ref);
    setExpandedRecords(previous => previous.includes(ref) ? previous : [...previous, ref]);
    requestAnimationFrame(() => document.getElementById(`record-${ref}`)?.scrollIntoView({ behavior: "smooth", block: "center" }));
  }
  function toggleRecord(recordId: string) {
    setExpandedRecords(previous => previous.includes(recordId)
      ? previous.filter(id => id !== recordId)
      : [...previous, recordId]);
  }
  function safeDetail(value: unknown): string {
    if (value === null || value === undefined) return "—";
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
    try { return JSON.stringify(value); } catch { return t("unavailableDetail"); }
  }
  function citationButtons(finding: Finding | { evidence_record_ids?: string[] }) {
    const refs = finding.evidence_record_ids ?? [];
    return <div className="citation-wrap">{refs.map(ref => {
      const observed = evidence?.observations.find(o => o.record_id === ref);
      return <button className="citation" type="button" key={ref} onClick={() => scrollToCitation(ref)} title={t("openRecord")}><Link2 size={12} /><span>{observed?.record_type ?? "record"}:</span><strong>{ref}</strong></button>;
    })}</div>;
  }
  function agentPanel(kind: "explain" | "plan") {
    const agent = kind === "explain" ? explain : plan;
    const isExplain = kind === "explain";
    return <Card className="agent-card" id={isExplain ? "explain-panel" : "plan-panel"}>
      <Head icon={isExplain ? BookOpen : ListChecks} title={t(isExplain ? "explainTitle" : "planTitle")} desc={t(isExplain ? "explainDesc" : "planDesc")}
        aside={<Chip tone={agent.phase === "accepted" ? "amber" : agent.phase === "no_findings" ? "neutral" : agent.phase === "rejected" ? "red" : agent.phase === "running" ? "blue" : "neutral"} icon={agent.phase === "accepted" ? CheckCircle2 : agent.phase === "rejected" ? XCircle : undefined}>{agent.phase === "accepted" ? (locale === "id" ? "Tervalidasi · Perlu ditinjau" : "Validated · Review needed") : t(agent.phase === "no_findings" ? "noModel" : agent.phase === "rejected" ? "rejected" : agent.phase === "running" ? "running" : "notRequested")}</Chip>} />
      {agent.phase === "not_requested" && <div className="agent-idle"><div className="agent-idle-icon"><ShieldCheck size={24} /></div><p>{isExplain ? t("explainDesc") : t("planDesc")}</p><button className="button primary" disabled={blocked || evidenceStatus !== "loaded"} onClick={() => void runAgent(kind)}><BookOpen size={16} />{t(isExplain ? "generateExplain" : "generatePlan")}<ArrowRight size={16} /></button></div>}
      {agent.phase === "running" && <div className="agent-idle"><LoaderCircle className="spin" size={26} /><strong>{t("running")}</strong><p>{!liveMode && t("demoAgentNotice")}</p></div>}
      {agent.phase === "rejected" && <div className="agent-failure"><div className="failure-title"><AlertCircle size={18} />{t("rejected")}</div><p>{agent.error?.message || t("failedBody")}</p><div><small>{t("rejectedCode")}</small><Emphasis>{agent.error?.code}</Emphasis></div>{agent.error?.guidance && <p>{t("errorGuidance")}: {agent.error.guidance}</p>}<p className="footnote">{t("failedBody")}</p><div className="buttonrow"><button className="button outline" onClick={() => document.getElementById("findings")?.scrollIntoView({ behavior: "smooth" })}><BookOpen size={15}/>{t("evidenceLinks")}</button><button className="button secondary" disabled={blocked} onClick={() => void runAgent(kind)}><RefreshCw size={15}/>{t("retry")}</button></div></div>}
      {isExplain && (agent.phase === "accepted" || agent.phase === "no_findings") && <div className="agent-result">
        {(agent.result as ExplainResult)?.hypotheses?.length ? (agent.result as ExplainResult).hypotheses.map((h, i) => <div key={i} className="result-block"><div className="result-label"><CheckCircle2 size={16}/><b>{pretty(h.hypothesis)}</b></div><p>{h.reason}</p>{citationButtons(h)}</div>) : <p className="muted">{t("noFindingsBody")}</p>}
        {(agent.result as ExplainResult)?.unresolved_questions?.map((q,i) => <div key={i} className="question-box"><CircleHelp size={17}/><div><b>{t("questions")}</b><p>{q}</p></div></div>)}
        <p className="footnote">{t("modelNotice")} {!liveMode && t("demoAgentNotice")}</p>
      </div>}
      {!isExplain && agent.phase === "accepted" && <div className="agent-result"><Chip tone="amber" icon={LockKeyhole}>{t("proposedOnly")}</Chip><div className="step-list">{(agent.result as PlanResult)?.actions?.map((a,i) => <div key={i} className="step-row"><span className="step-number">{i+1}</span><div><b>{t(a.action === "read_only_source_query" ? "actionQuery" : a.action === "manual_review" ? "actionReview" : "actionStop")}</b>{a.source_system && <span className="subtle-source"> · {a.source_system}</span>}<p>{a.reason}</p>{citationButtons(a)}</div></div>)}</div><p className="footnote"><Info size={14}/>{t("planNoExec")} {!liveMode && t("demoAgentNotice")}</p></div>}
      <ThinkingTrace t={t} phase={agent.phase} live={liveMode} type={kind}/>
      <div className="agent-footer"><span><LockKeyhole size={13}/>{t("safeValue")}</span><span>{t("noAutomatic")}</span></div>
    </Card>;
  }

  const navItems: { view: Screen; label: TextKey; icon: ComponentType<{ size?: number }> }[] = [
    { view: "explorer", label: "caseExplorer", icon: FolderOpen }, { view: "investigation", label: "investigations", icon: ClipboardCheck },
    { view: "activity", label: "reviewActivity", icon: NotebookPen }, { view: "audit", label: "auditHistory", icon: FileClock }, { view: "settings", label: "settings", icon: Settings2 },
  ];

  return <div className="app-shell">
    <aside className={`sidebar ${collapsed ? "collapsed" : ""}`}>
      <div className="brand"><div className="logo" aria-hidden="true"><span className="tbcare-logo-letter">T</span></div><div className="brand-text"><strong>TBCare</strong><small>{t("tagline")}</small></div></div>
      <nav className="side-nav" aria-label="Primary navigation">{navItems.map(item => <button key={item.view} className={`nav-item ${view === item.view ? "active" : ""}`} aria-current={view === item.view ? "page" : undefined} onClick={() => item.view === "investigation" && !caseId ? void loadCase(selected) : move(item.view)} title={t(item.label)}><item.icon size={19}/><span>{t(item.label)}</span>{view === item.view && <span className="nav-active-dot"/>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="side-art" aria-hidden="true"><ShieldCheck size={29} strokeWidth={1.6}/></div><strong>{t("workspace")}</strong><p>{t("whatItDoesBody")}</p><div className="side-small"><ShieldCheck size={14}/>{t("synthetic")}</div></div>
    </aside>
    <div className="main-shell">
      <header className="topbar"><button className="collapse-button" onClick={() => setCollapsed(v => !v)} aria-label="Toggle sidebar"><PanelLeftClose size={19}/></button><span className="top-location"><ClipboardList size={16}/>{t("workspace")}</span><div className="top-spacer"/><div className="top-pill"><ShieldCheck size={14}/>{t("sourceOnly")}</div><div className="lang-control"><Languages size={16}/><select aria-label={t("lang")} value={locale} onChange={e => setLocale(e.target.value as Locale)}><option value="en">English</option><option value="id">Indonesia</option></select><ChevronDown size={13}/></div><NotificationCenter t={t} notices={notices} open={noticeOpen}
        onToggle={() => setNoticeOpen(v => !v)} onMarkRead={() => setNotices(prev => prev.map(n => ({ ...n, read: true })))}
        onClear={() => { setNotices([]); setToastDismissed(null); }}
        onSelect={n => { setNotices(prev => prev.map(entry => entry.id === n.id ? { ...entry, read: true } : entry)); setNoticeOpen(false); if (n.caseId && ids.includes(n.caseId)) { if (n.caseId === caseId) move("investigation"); else void loadCase(n.caseId); } }}
        browserEnabled={desktopNotify} onBrowserToggle={() => void toggleDesktopNotifications()}
        browserAvailable={browserAvailable}/><div className="user-pill"><span className="avatar">DR</span><div><strong>DEMO-REVIEWER</strong><small>{t("demoReviewer")}</small></div></div></header>
      <main className="main-body">
        <div className="ribbon" role="status" aria-live="polite"><span className={`connection-status state-${backendConnection}`}>{t(backendConnection === "demo" ? "demoMode" : backendConnection === "checking" ? "backendChecking" : backendConnection === "connected" ? "backendConnected" : "backendUnavailable")}</span><span className="ribbon-sep"/>{t("headerNotice")}{backendConnection === "unavailable" && <button className="connection-retry" type="button" onClick={() => void retryBackendConnection()}>{t("retryConnection")}</button>}<span className="ribbon-right">{liveMode ? "LOCAL / 127.0.0.1:8765" : "OFFLINE FIXTURES · 001 / 009 / 018"}</span></div>
        {appError && <div className="global-alert"><AlertCircle size={17}/>{appError}<button onClick={() => setAppError("")} aria-label="Close">×</button></div>}

        {view === "explorer" && <>
          <div className="page-heading"><div><div className="eyebrow"><span className="eyebrow-line"/>{t("workspace")}</div><h1>{t("exploreTitle")}</h1><p>{t("exploreSub")}</p></div><span className="demo-tag"><ShieldCheck size={16}/>{t("synthetic")}</span></div>
          <div className="metrics"><div className="metric"><span className="metric-icon blue"><Layers3 size={21}/></span><div><span>{t("totalCases")}</span><strong>{ids.length}</strong><small>CASE-TB-001–036</small></div></div><div className="metric"><span className="metric-icon gray"><Clock3 size={21}/></span><div><span>{t("notChecked")}</span><strong>{ids.length - inspectedCount}</strong><small>{t("sessionOnly")}</small></div></div><div className="metric"><span className="metric-icon orange"><AlertCircle size={21}/></span><div><span>{t("observedFindings")}</span><strong>{findingsCount}</strong><small>{t("sessionOnly")}</small></div></div><div className="metric"><span className="metric-icon teal"><NotebookPen size={21}/></span><div><span>{t("localNotes")}</span><strong>{noteCaseCount}</strong><small>{t("notResolved")}</small></div></div></div>
          <div className="explorer-grid"><div className="left-column">
            <Card className="case-table-card"><div className="case-toolbar"><div><h3>{t("caseExplorer")}</h3><p>{t("sessionOnly")}</p></div><div className="search-field"><Search size={16}/><input aria-label={t("searchCases")} type="search" value={search} onChange={e => setSearch(e.target.value)} placeholder={t("searchCases")} /></div></div>
              <div className="filter-row"><Filter size={16} className="filter-icon"/>{([ ["all","all"], ["not_checked","notChecked"], ["findings","findings"], ["notes","withNotes"]] as const).map(([f,key])=><button key={f} onClick={()=>setFilter(f)} className={`filter-pill ${filter===f?"on":""}`} aria-pressed={filter===f}>{t(key)}{f==="all"?<b>{ids.length}</b>:f==="not_checked"?<b>{ids.length-inspectedCount}</b>:f==="findings"?<b>{findingCaseCount}</b>:<b>{noteCaseCount}</b>}</button>)}</div>
              <div className="table-scroll"><table className="data-table case-list"><caption className="sr-only">{t("caseExplorer")}: {rows.length} / {ids.length}</caption><thead><tr><th scope="col">{t("caseId")}</th><th scope="col">{t("sourceMode")}</th><th scope="col">{t("evidenceState")}</th><th scope="col">{t("findingCount")}</th><th>{t("notes")}</th><th>{t("action")}</th></tr></thead><tbody>{rows.map(id=>{const it=inspected[id];return <tr key={id} className={selected===id?"selected-row":""}><th scope="row"><button type="button" className="case-select" aria-pressed={selected===id} onClick={() => setSelected(id)}><FileText size={16}/><b>{id}</b></button></th><td><span className="source-mode-cell">{sourceMode === "ui_fixture" ? t("demoMode") : sourceMode === "unknown" ? t("unknown") : t("localMode")}</span></td><td>{it?<Chip tone={it.stale?"red":it.impaired?"amber":"blue"} icon={it.stale?AlertCircle:it.impaired?AlertCircle:CheckCircle2}>{it.stale?t("snapshotStale"):it.impaired?t("partialSource"):t("sourceReadComplete")}</Chip>:<Chip>{t("notChecked")}</Chip>}</td><td>{it ? it.findings > 0 ? <Chip tone="amber" icon={AlertCircle}>{it.findings}</Chip>:<Chip tone="neutral">0</Chip> : <span className="muted">—</span>}</td><td><span className="notes-mini"><NotebookPen size={14}/>{noteCounts[id] ?? 0}</span></td><td><button className="table-action" disabled={(liveMode && backendConnection!=="connected") || (!liveMode && !demoFixtures.includes(id))} onClick={e=>{e.stopPropagation();void loadCase(id);}}>{t("open")}<ArrowRight size={14}/></button></td></tr>})}</tbody></table>{rows.length===0&&<div className="empty-table">{t("notChecked")}</div>}</div><div className="table-bottom">{rows.length} / {ids.length} {t("recordsShown")} <span>{t("notResolved")}</span></div></Card>
            <Card className="activity-preview"><Head icon={Activity} title={t("recent")} aside={<button className="text-link" onClick={()=>move("activity")}>{t("viewDetails")}<ArrowRight size={14}/></button>}/>{Object.values(reviews).flat().length===0?<div className="small-empty"><NotebookPen size={21}/>{t("noneRecorded")}</div>:Object.values(reviews).flat().slice(-3).reverse().map(r=><div className="note-line" key={r.review_event_id}><span className="avatar small">DR</span><div><b>{r.case_id}</b><p>{r.note || pretty(r.disposition)}</p></div><small>{utcDate(r.recorded_at_utc)}</small></div>)}</Card>
          </div><div className="right-column">
            <Card className="selected-preview"><div className="preview-kicker">{t("preview")}</div><div className="preview-id"><div className="folder-large"><FileText size={26}/></div><div><h2>{selected}</h2><Chip tone="violet">{t("synthetic")}</Chip></div></div><div className="preview-fields"><div><span>{t("evidenceState")}</span><strong>{inspected[selected]?(inspected[selected].stale?t("snapshotStale"):inspected[selected].impaired?t("partialSource"):t("sourceReadComplete")):t("notChecked")}</strong></div><div><span>{t("findingCount")}</span><strong>{inspected[selected]?.findings ?? "—"}</strong></div><div><span>{t("agentState")}</span><strong>{t("notRequested")}</strong></div><div><span>{t("localNotes")}</span><strong>{noteCounts[selected]??0}</strong></div></div><p className="preview-help">{t("demoHint")}</p><button className="button primary full" disabled={(liveMode && backendConnection!=="connected") || (!liveMode && !demoFixtures.includes(selected))} onClick={()=>void loadCase(selected)}>{t("open")}<ArrowRight size={17}/></button>{!liveMode && !demoFixtures.includes(selected) && <p className="preview-help">{t("unavailableFixture")}</p>}</Card>
            <Card className="scenarios"><Head icon={ListChecks} title={t("exampleScenarios")}/>{([ ["CASE-TB-001", "firstCase"], ["CASE-TB-009", "nineCase"], ["CASE-TB-018", "eighteenCase"] ] as const).map(([id, key],index)=><button key={id} className="scenario" onClick={()=>void loadCase(id)} disabled={!ids.includes(id)}><span className={`scenario-number s${index}`}>0{index+1}</span><span><strong>{id}</strong><small>{t(key)}</small></span><ChevronRight size={17}/></button>)}</Card>
            <div className="safety-note"><ShieldCheck size={22}/><div><b>{t("whatItDoes")}</b><p>{t("whatItDoesBody")}</p></div></div>
          </div></div>
        </>}

        {view === "investigation" && <>
          <div className="page-heading investigation-heading"><div><button className="back-link" onClick={()=>move("explorer")}><ArrowLeft size={15}/>{t("back")}</button><h1>{t("caseWorkspace")}</h1><p>{t("caseSub")}</p></div><div className="heading-actions"><Chip tone="violet" icon={ShieldCheck}>{t("synthetic")}</Chip><button className="button outline" disabled={!caseId || evidenceStatus === "loading"} onClick={()=>caseId&&void loadCase(caseId)}><RefreshCw size={15}/>{t("refresh")}</button></div></div>
          <div className="case-topbar"><div className="case-top-icon"><FileText size={23}/></div><div className="case-top-name"><small>{t("caseId")}</small><strong>{caseId}</strong></div><div className="case-top-divider"/><div className="case-top-item"><small>{t("sourceMode")}</small><strong>{sourceMode === "ui_fixture" ? t("demoMode") : pretty(sourceMode)}</strong></div><div className="case-top-item"><small>{t("evidenceState")}</small><Chip tone={evidenceStatus === "stale" || evidenceStatus === "failed" ? "red" : evidenceStatus === "loaded" ? "blue" : "neutral"}>{evidenceStatus === "loaded" ? sourceSummary : evidenceStatus === "loading" ? t("loading") : evidenceStatus === "failed" ? t("readFailed") : evidenceStatus === "stale" ? t("snapshotStale") : t("notChecked")}</Chip></div><div className="case-top-item"><small>{t("observations")}</small><strong>{evidence?.observations.length ?? "—"}</strong></div><div className="case-top-item"><small>{t("findings")}</small><strong>{evidence?.exceptions.length ?? "—"}</strong></div><div className="case-top-item approval"><small>{t("status")}</small><Chip tone="amber" icon={AlertCircle}>{t("safeValue")}</Chip></div></div>
          <div className="journey">{([ ["stageInspect","stageInspectSub",1], ["stageExplain","stageExplainSub",2], ["stagePropose","stageProposeSub",3], ["stageReview","stageReviewSub",4] ] as const).map(([k,sub,n],i)=><button key={n} className={`journey-stage ${i===0 && evidenceStatus === "loaded" ? "current" : ""}`} onClick={()=>document.getElementById(i===0?"sources":i===1?"explain-panel":i===2?"plan-panel":"review")?.scrollIntoView({behavior:"smooth",block:"start"})}><span className="journey-bubble">{i===0?<Check size={17}/>:n}</span><span><strong>{t(k)}</strong><small>{t(sub)}</small></span></button>)}</div>
          <IntentStrip t={t} evidenceReady={evidenceStatus === "loaded"} stale={evidenceStatus === "stale"} explain={explain.phase} plan={plan.phase} notes={caseNotes.length}/>
          {evidenceStatus === "loading"&&<div className="screen-loading"><LoaderCircle size={26} className="spin"/><p>{t("loading")}</p></div>}
          {evidenceStatus === "failed"&&<div className="screen-loading error-state"><AlertCircle size={26}/><p>{t("readFailed")}: {appError}</p><button className="button primary" onClick={()=>caseId&&void loadCase(caseId)}>{t("refresh")}</button></div>}
          {evidenceStatus === "stale"&&<div className="global-alert"><AlertCircle size={17}/>{t("snapshotStale")}<button className="button small" onClick={()=>caseId&&void loadCase(caseId)}>{t("refresh")}</button></div>}
          {evidence&&<>
            <div className="detail-grid"><div className="left-column">
              <Card id="sources"><Head icon={Database} title={t("sources")} desc={t("sourceHelp")} aside={<Chip tone="blue">{sourceNames.length} {t("sources")}</Chip>}/><div className="source-status-list" role="list">{sourceNames.map(name=>{const source=evidence.source_checks.filter(x=>x.source_system===name).sort((a,b)=>b.attempt-a.attempt)[0];const status=source?.status??"not_checked";return <div className="source-status-row" role="listitem" key={name}><strong>{name}</strong><span className="source-attempt">{t("queryAttempt")} {source?.attempt ?? "—"}</span><Chip tone={status==="available"?"green":status==="not_found"||status==="not_checked"?"neutral":"red"}>{formatStatus(status)}</Chip></div>})}</div></Card>
              <Card id="retrieved-evidence"><Head icon={Layers3} title={t("observations")} desc={t("selectCitation")} aside={<Chip tone="blue">{evidence.observations.length} {t("records")}</Chip>}/><div className="table-scroll"><table className="data-table source-table"><caption className="sr-only">{t("observations")} · {evidence.observations.length}</caption><thead><tr><th scope="col">{t("sourceType")}</th><th scope="col">{t("businessId")}</th><th scope="col">{t("rowId")}</th><th scope="col">{t("subjectRef")}</th><th scope="col">{t("eventTime")}</th><th scope="col">{t("sourceDetails")}</th></tr></thead><tbody>{evidence.observations.map(o=>{const isExpanded=expandedRecords.includes(o.record_id);return <Fragment key={o.record_id}><tr className={flashRecord===o.record_id?"flash-row":""} id={`record-${o.record_id}`}><td><span className="source-name">{o.record_type}</span></td><td><Emphasis>{o.record_id}</Emphasis></td><td><Emphasis>{o.source_record_id}</Emphasis></td><td><Emphasis>{o.subject_ref}</Emphasis></td><td><span className="small-date">{utcDate(o.observed_at)}</span></td><td><button type="button" className="record-detail-toggle" aria-expanded={isExpanded} aria-controls={isExpanded ? `details-${o.record_id}` : undefined} onClick={()=>toggleRecord(o.record_id)}>{isExpanded?<ChevronDown size={14}/>:<ChevronRight size={14}/>} {isExpanded?t("hideDetails"):t("sourceDetails")}</button></td></tr>{isExpanded && <tr className="record-details-row" id={`details-${o.record_id}`}><td colSpan={6}><dl className="record-detail-grid"><div><dt>{t("businessId")}</dt><dd><Emphasis>{o.record_id}</Emphasis></dd></div><div><dt>{t("rowId")}</dt><dd><Emphasis>{o.source_record_id}</Emphasis></dd></div><div><dt>{t("subjectRef")}</dt><dd><Emphasis>{o.subject_ref}</Emphasis></dd></div>{Object.entries(o.details??{}).slice(0,16).map(([key,value])=><div key={key}><dt>{pretty(key)}</dt><dd>{safeDetail(value)}</dd></div>)}</dl><p className="record-detail-note">{t("detailEvidenceOnly")}</p></td></tr>}</Fragment>})}</tbody></table></div><p className="under-table"><Info size={14}/>{t("langHelp")}</p></Card>
              {agentPanel("plan")}
              {liveMode && <Card className="server-activity"><Head icon={Activity} title={locale === "id" ? "Aktivitas agen terverifikasi" : "Verified agent activity"} desc={locale === "id" ? "Tahapan proses yang benar-benar tercatat di server. Bukan pemikiran internal model." : "Actual server checkpoints. Not the model's private reasoning."} aside={<Chip tone="blue">{serverActivity?.total ?? "—"}</Chip>}/><div className="server-activity-rows">{serverActivity?.events.length ? serverActivity.events.slice(-12).reverse().map(event => <div className="server-event" key={event.event_id}><b>{event.operation}</b><span>{pretty(event.state)}</span><time dateTime={event.occurred_at_utc}>{utcDate(event.occurred_at_utc)}</time></div>) : <p className="padded-note">{locale === "id" ? "Belum ada aktivitas server yang dapat diverifikasi." : "No verified server activity is available yet."}</p>}</div><p className="footnote">{locale === "id" ? "Log aktivitas aplikasi lokal terpisah dari riwayat Meterless dan catatan tinjauan." : "Local application activity is separate from Meterless and review notes."}</p></Card>}
              <Card id="audit" className="audit-card"><Head icon={FileClock} title={t("auditTitle")} desc={t("auditDesc")} aside={<button className="text-link" disabled={!liveMode||auditStatus==="loading"} onClick={()=>caseId&&void loadAudit(caseId,latest.current)}><RefreshCw size={14}/>{t("reloadAudit")}</button>}/>{!liveMode?<div className="empty-audit"><FileClock size={28}/><p>{t("auditNoDemo")}</p></div>:auditStatus==="loading"?<p className="padded-note">{t("loading")}</p>:auditStatus==="unavailable"?<div className="empty-audit"><AlertCircle size={23}/><p>{t("auditUnavailable")} {auditError}</p></div>:auditStatus==="empty"?<div className="empty-audit"><Info size={22}/><p>{t("auditEmpty")}</p></div>:audit?<><div className="audit-stats"><Chip tone="blue">{audit.event_count} events</Chip><Chip>{audit.audit_count} audit records</Chip>{audit.truncated&&<Chip tone="amber">Truncated</Chip>}</div><div className="table-scroll"><table className="data-table"><thead><tr><th>{t("eventId")}</th><th>{t("eventType")}</th><th>{t("eventAt")}</th></tr></thead><tbody>{audit.events.map(ev=><tr key={ev.event_id}><td><Emphasis>{ev.event_id}</Emphasis></td><td>{ev.event_type}</td><td>{utcDate(ev.event_at)}</td></tr>)}</tbody></table></div></>:null}<p className="footnote"><Info size={14}/>{t("auditLegend")}</p></Card>
            </div><div className="right-column">
              <Card id="findings"><Head icon={AlertCircle} title={t("findingsTitle")} desc={t("findingsSub")} aside={<Chip tone="amber">{evidence.exceptions.length} {t("findingCount")}</Chip>}/>{!hasFindings?<div className="no-finding"><Info size={21}/><div><strong>{t("noFindingsTitle")}</strong><p>{t("noFindingsBody")}</p></div></div>:evidence.exceptions.map((finding,i)=><div key={i} className="finding-row"><span className="finding-number">{i+1}</span><div><div className="finding-title"><b>{pretty(finding.category)}</b><Chip tone="amber">{t("unresolved")}</Chip></div><p>{finding.description}</p><div className="evidence-caption">{t("evidenceLinks")}</div>{citationButtons(finding)}</div></div>)}</Card>
              {agentPanel("explain")}
              <HumanCheckpoint t={t} ready={evidenceStatus === "loaded"} hasFinding={hasFindings}
                evidenceReviewed={evidenceReviewed} scopeAcknowledged={scopeAcknowledged}
                onEvidenceReviewed={setEvidenceReviewed} onScopeAcknowledged={setScopeAcknowledged}
                onInspect={() => document.getElementById("retrieved-evidence")?.scrollIntoView({behavior:"smooth",block:"start"})}
                onAgent={() => document.getElementById("explain-panel")?.scrollIntoView({behavior:"smooth",block:"start"})}
                onReview={() => document.getElementById("review")?.scrollIntoView({behavior:"smooth",block:"start"})}/>
              <Card id="review"><Head icon={UserRoundCheck} title={t("reviewTitle")} desc={t("reviewDesc")}/>{!hasFindings?<div className="small-empty"><Info size={18}/>{t("noteNotAvailable")}</div>:<div className="review-form"><div className="form-grid"><label>{t("reviewer")}<input value="DEMO-REVIEWER" readOnly /></label><label>{t("disposition")}<select value={disposition} onChange={e=>{setDisposition(e.target.value);reviewRequestId.current=null;}}><option value="request_source_verification">{t("requestSource")}</option><option value="escalate_admin_review">{t("escalateAdmin")}</option><option value="reviewed_unresolved">{t("reviewedUnresolved")}</option></select></label></div><label>{t("selectFinding")}<select value={reviewIndex} onChange={e=>{setReviewIndex(Number(e.target.value));reviewRequestId.current=null;}}>{evidence.exceptions.map((f,i)=><option value={i} key={i}>{i+1}. {pretty(f.category)}</option>)}</select></label><label>{t("reviewText")}<textarea value={reviewNote} maxLength={280} minLength={12} onChange={e=>{setReviewNote(e.target.value);reviewRequestId.current=null;}} placeholder={t("notePlaceholder")} rows={3}/><small className="charcount">{reviewNote.length}/280</small></label><label className="check-confirm"><input type="checkbox" checked={checked} onChange={e=>setChecked(e.target.checked)} /><span>{t("confirm")}</span></label>{(!evidenceReviewed || !scopeAcknowledged) && <p className="checkpoint-gate-notice"><LockKeyhole size={14}/>{t("humanGateComplete")}</p>}<button className="button primary full" disabled={blocked||!checked||!evidenceReviewed||!scopeAcknowledged||saving||reviewNote.trim().length<12} onClick={()=>void saveReview()}>{saving?<LoaderCircle className="spin" size={16}/>:<NotebookPen size={16}/>} {saving?t("saving"):t(liveMode?"save":"previewSave")}</button>{saveStatus&&<p className="save-status">{saveStatus}</p>}</div>}
                <div className="review-history"><div className="history-title"><Clock3 size={16}/><b>{t("noteHistory")}</b><Chip>{caseNotes.length}</Chip></div><p className="helper">{t("historySub")}</p>{caseNotes.length?caseNotes.slice().reverse().map(note=><div className="review-entry" key={note.review_event_id}><div className="review-entry-top"><strong>{note.reviewer_label}</strong><small>{utcDate(note.recorded_at_utc)}</small></div><p>{note.note}</p><small>{pretty(note.disposition)}</small></div>):<div className="empty-note">{t("noNotes")}</div>}</div>
              </Card>
            </div></div>
          </>}
        </>}

        {view === "activity" && <><div className="page-heading"><div><h1>{t("activityPage")}</h1><p>{t("activitySub")}</p></div><Chip tone="blue" icon={NotebookPen}>{t("localNotes")}</Chip></div><Card className="full-content"><Head icon={Activity} title={t("recent")} desc={t("historySub")}/>{Object.values(reviews).flat().length===0?<div className="screen-loading compact"><NotebookPen size={26}/>{t("noneRecorded")}</div>:Object.values(reviews).flat().slice().reverse().map(r=><div className="activity-row" key={r.review_event_id}><span className="avatar small">DR</span><div><strong>{r.case_id} · {r.reviewer_label}</strong><p>{r.note||pretty(r.disposition)}</p><small>{pretty(r.disposition)} · {utcDate(r.recorded_at_utc)}</small></div><button className="button outline small" onClick={()=>void loadCase(r.case_id)}>{t("open")}<ArrowRight size={13}/></button></div>)}{liveMode&&<p className="footnote">{t("sessionOnly")}</p>}</Card></>}
        {view === "audit" && <><div className="page-heading"><div><h1>{t("auditPage")}</h1><p>{t("auditPageSub")}</p></div><Chip tone="blue" icon={LockKeyhole}>{t("readonly")}</Chip></div><Card className="full-content"><Head icon={FileClock} title={t("auditTitle")} desc={t("auditDesc")}/><div className="standalone-audit"><div><label>{t("caseId")}</label><select value={selected} onChange={e=>setSelected(e.target.value)}>{ids.map(id=><option key={id} value={id}>{id}</option>)}</select></div><button className="button primary" onClick={()=>void loadCase(selected)}>{t("open")}<ArrowRight size={16}/></button></div><div className="empty-audit"><Info size={23}/><p>{t("auditNoDemo")} {t("auditLegend")}</p></div></Card></>}
        {view === "settings" && <><div className="page-heading"><div><h1>{t("settingsTitle")}</h1><p>{t("settingsSub")}</p></div></div><div className="settings-grid"><Card><Head icon={Languages} title={t("lang")}/><div className="setting-row"><span>English / Bahasa Indonesia</span><div className="segmented"><button className={locale==="en"?"chosen":""} onClick={()=>setLocale("en")}>EN</button><button className={locale==="id"?"chosen":""} onClick={()=>setLocale("id")}>ID</button></div></div><p className="helper">{t("langHelp")}</p></Card><Card><Head icon={ShieldCheck} title={t("integration")}/><Chip tone={liveMode?"green":"violet"}>{t(liveMode?"localMode":"demoMode")}</Chip><p className="settings-text">{t(liveMode?"localExplain":"demoExplain")}</p><p className="footnote">{t("privacy")}</p></Card></div></>}
        <footer className="bottom-footer"><span><ClipboardList size={15}/> TBCare · {t("synthetic")}</span><span>{t("privacy")}</span></footer>
      </main>
      <ActivityToast t={t} notice={toastDismissed !== mostRecentNotice?.id ? mostRecentNotice : undefined} onDismiss={setToastDismissed}/>
    </div>
  </div>;
}
