"use client";

import { AlertCircle, ArrowRight, Bell, BellRing, Check, CheckCheck, CheckCircle2, Circle, Info, LockKeyhole, LoaderCircle, ShieldCheck, Sparkles, X, XCircle } from "lucide-react";
import type { AgentPhase } from "@/lib/types";
import type { TextKey } from "@/lib/i18n";

type T = (key: TextKey) => string;
export type ActivityNotice = {
  id: string; titleKey: TextKey; caseId?: string; detail?: string;
  tone: "info" | "success" | "warning" | "error"; at: number; read: boolean;
};

export function IntentStrip({ t, evidenceReady, explain, plan, notes, stale }: {
  t: T; evidenceReady: boolean; explain: AgentPhase; plan: AgentPhase;
  notes: number; stale: boolean;
}) {
  const phases = [
    { title: t("intentInspect"), detail: t("intentInspectDesc"), done: evidenceReady && !stale, active: !evidenceReady || stale },
    { title: t("intentExplain"), detail: t("intentExplainDesc"), done: explain === "accepted" || explain === "no_findings", active: explain === "running" || explain === "rejected" },
    { title: t("intentPropose"), detail: t("intentProposeDesc"), done: plan === "accepted", active: plan === "running" || plan === "rejected" },
    { title: t("intentHuman"), detail: t("intentHumanDesc"), done: false, active: notes > 0 },
  ];
  return <section className="agentic-intent surface" aria-label={t("intentTitle")}>
    <div className="agentic-intent-heading"><div><span className="intent-kicker"><ShieldCheck size={14} /> {t("intentTitle")}</span><h3>{t("intentLead")}</h3><p>{t("intentNotice")}</p></div><span className="intent-readonly"><LockKeyhole size={13}/>{t("intentReadOnly")}</span></div>
    <div className="intent-states">{phases.map((step, i) => <div className={`intent-stage ${step.active ? "intent-active" : ""}`} key={i}>
      <div className="intent-stage-head"><span className={`intent-circle ${step.done ? "intent-done" : ""}`}>{step.done ? <Check size={14} /> : i + 1}</span><strong>{step.title}</strong></div><p>{step.detail}</p>
    </div>)}</div>
  </section>;
}

export function ThinkingTrace({ t, phase, live, type }: { t: T; phase: AgentPhase; live: boolean; type: "explain" | "plan" }) {
  const idle = phase === "not_requested";
  const running = phase === "running";
  const rejected = phase === "rejected";
  const complete = phase === "accepted";
  const noModel = phase === "no_findings";
  const steps = [
    { text: t("thinkingStepRequest"), state: idle ? "idle" : "done" },
    { text: t("thinkingStepWait"), state: idle ? "idle" : running ? "active" : "done" },
    { text: t("thinkingStepVerify"), state: idle || running ? "idle" : rejected ? "failed" : "done" },
  ];
  if (noModel) return <div className="thinking-trace" role="status" aria-live="polite"><div className="thinking-heading"><span className="thinking-icon"><Info size={15}/></span><strong>{t("thinkingTitle")} · {type === "explain" ? "CaseLens" : "NextStep"}</strong></div><p className="thinking-disclaimer"><Info size={13}/>{t("thinkingNoModel")}</p></div>;
  return <div className="thinking-trace" role="status" aria-live="polite">
    <div className="thinking-heading"><span className="thinking-icon">{running ? <LoaderCircle className="spin" size={15}/> : <Info size={15}/>}</span><strong>{t("thinkingTitle")} · {type === "explain" ? "CaseLens" : "NextStep"}</strong><span className="thinking-state-label">{t(idle ? "notRequested" : running ? "running" : rejected ? "rejected" : complete ? "accepted" : "notRequested")}</span></div>
    <div className="thinking-steps">{steps.map((s, i) => <div className={`thinking-step state-${s.state}`} key={i}>
      <span className="thinking-marker">{s.state === "done" ? <Check size={12}/> : s.state === "failed" ? <X size={12}/> : s.state === "active" ? <LoaderCircle size={12} className="spin"/> : <Circle size={11}/>}</span>
      <span>{s.text}</span>
    </div>)}</div>
    <p className="thinking-disclaimer"><Info size={13}/>{t(live ? "thinkingLiveDisclaimer" : "thinkingDemoDisclaimer")}</p>
  </div>;
}

export function HumanCheckpoint({ t, evidenceReviewed, scopeAcknowledged, onEvidenceReviewed, onScopeAcknowledged, onInspect, onAgent, onReview, ready, hasFinding }: {
  t: T; evidenceReviewed: boolean; scopeAcknowledged: boolean;
  onEvidenceReviewed: (v: boolean) => void; onScopeAcknowledged: (v: boolean) => void;
  onInspect: () => void; onAgent: () => void; onReview: () => void;
  ready: boolean; hasFinding: boolean;
}) {
  return <section className="human-checkpoint surface" aria-label={t("humanGateTitle")}>
    <div className="checkpoint-head"><div className="checkpoint-icon"><ShieldCheck size={23}/></div><div><h3>{t("humanGateTitle")}</h3><p>{t("humanGateDesc")}</p></div><span className="checkpoint-counter">{Number(evidenceReviewed) + Number(scopeAcknowledged)} / 2</span></div>
    <div className="checkpoint-steps">
      <div className="checkpoint-row"><input type="checkbox" aria-label={t("humanGateEvidence")} disabled={!ready} checked={evidenceReviewed} onChange={e => onEvidenceReviewed(e.target.checked)}/><span><b>{t("humanGateEvidence")}</b><small>{t("humanGateEvidenceHint")}</small></span><button type="button" onClick={onInspect} disabled={!ready} className="button outline small">{t("humanGateSeeEvidence")} <ArrowRight size={13}/></button></div>
      <div className="checkpoint-row"><input type="checkbox" aria-label={t("humanGateScope")} disabled={!ready} checked={scopeAcknowledged} onChange={e => onScopeAcknowledged(e.target.checked)}/><span><b>{t("humanGateScope")}</b><small>{t("humanGateScopeHint")}</small></span><button type="button" onClick={onAgent} disabled={!ready} className="button outline small">{t("humanGateSeeAgents")} <ArrowRight size={13}/></button></div>
    </div>
    <div className="checkpoint-footer"><div><Info size={16}/><span>{t(hasFinding ? "humanGatePending" : "humanGateNoFinding")}</span></div><button className="button primary small" type="button" onClick={onReview} disabled={!ready || !hasFinding}>{t("humanGateGoReview")} <ArrowRight size={14}/></button></div>
  </section>;
}

export function NotificationCenter({ t, notices, open, onToggle, onMarkRead, onClear, onSelect, browserEnabled, onBrowserToggle, browserAvailable }: {
  t: T; notices: ActivityNotice[]; open: boolean; onToggle: () => void;
  onMarkRead: () => void; onClear: () => void; onSelect: (notice: ActivityNotice) => void;
  browserEnabled: boolean; onBrowserToggle: () => void; browserAvailable: boolean;
}) {
  const unread = notices.filter(x => !x.read).length;
  return <div className="notification-wrapper">
    <button type="button" aria-label={t("activityCenterTitle")} aria-expanded={open} aria-controls="agent-notification-popover" onClick={onToggle} className="notification-trigger"><Bell size={19}/>{unread > 0 && <span className="notification-counter">{unread > 9 ? "9+" : unread}</span>}</button>
    {open && <div className="notification-popover" id="agent-notification-popover" role="region" aria-label={t("activityCenterTitle")}>
      <div className="notifications-heading"><div><BellRing size={18}/><strong>{t("activityCenterTitle")}</strong></div><button type="button" className="icon-only" aria-label={t("close")} onClick={onToggle}><X size={17}/></button></div>
      <p className="notification-intro">{t("activityCenterDesc")}</p>
      <div className="notifications-actions"><button type="button" onClick={onMarkRead} disabled={!unread}><CheckCheck size={14}/>{t("markRead")}</button><button type="button" onClick={onClear} disabled={!notices.length}>{t("clearActivity")}</button></div>
      <div className="notifications-list" aria-live="polite">{!notices.length ? <div className="notification-empty"><Bell size={21}/><p>{t("noActivity")}</p></div> : notices.map(n => <button type="button" key={n.id} onClick={() => onSelect(n)} className={`notification-entry notification-${n.tone} ${n.read ? "is-read" : ""}`}><span className="notification-type-icon">{n.tone === "error" ? <XCircle size={16}/> : n.tone === "success" ? <CheckCircle2 size={16}/> : n.tone === "warning" ? <AlertCircle size={16}/> : <Info size={16}/>}</span><span className="notification-entry-text"><b>{t(n.titleKey)}</b><small>{[n.caseId,n.detail].filter(Boolean).join(" · ")}</small><small>{new Date(n.at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</small></span>{!n.read && <span className="notification-dot"/>}</button>)}</div>
      <div className="notification-settings"><div><strong>{t("tabNotificationTitle")}</strong><p>{t("tabNotificationHint")}</p></div><button type="button" className="button outline small" onClick={onBrowserToggle} disabled={!browserAvailable}>{browserEnabled ? t("turnOff") : t("enable")}</button></div>
      <p className="notification-disclaimer">{t("notificationNoBackend")}</p>
    </div>}
  </div>;
}

export function ActivityToast({ t, notice, onDismiss }: { t: T; notice?: ActivityNotice; onDismiss: (id: string) => void }) {
  if (!notice) return null;
  return <div className={`activity-toast notice-${notice.tone}`} role="status" aria-live="polite"><span>{notice.tone === "success" ? <CheckCircle2 size={19}/> : notice.tone === "error" ? <XCircle size={19}/> : <Info size={19}/>}</span><div><strong>{t(notice.titleKey)}</strong><p>{[notice.caseId,notice.detail].filter(Boolean).join(" · ")}</p></div><button type="button" aria-label={t("close")} onClick={() => onDismiss(notice.id)}><X size={17}/></button></div>;
}
