/* TB-CareOS local product MVP. Render untrusted evidence with textContent only. */
"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  ids: [], current: null, evidence: null, generation: 0, busy: false,
  reviewRequestId: null,
  // Source findings are remembered only for cases opened in this browser session.
  // Local reviewer notes are loaded separately; neither marks a case "resolved".
  inspected: new Map(), localNotes: new Map(), sourceMode: null,
  activitySeen: new Map(), activityUnread: new Set(), activityPending: false,
  workflow: {
    evidence: "not_checked", explain: "not_requested", plan: "not_requested",
    reviewCount: 0, audit: "not_checked",
  },
};
const SOURCE_NAMES = ["cases","screening_events","lab_orders","lab_results","followup_events"];
const label = (name) => name.replaceAll("_"," ");
function el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = String(text);
  return node;
}
function clear(id) { $(id).replaceChildren(); }
function showError(message) { $("error").hidden = false; $("error").textContent = message; }
function hideError() { $("error").hidden = true; $("error").textContent = ""; }
async function request(path, opts) {
  const response = await fetch(path, { cache: "no-store", ...opts });
  let data;
  try { data = await response.json(); }
  catch { throw new Error("Server returned an unreadable response."); }
  if (!response.ok) {
    const error = new Error(data.error || "Request did not complete.");
    error.code = typeof data.error_code === "string" ? data.error_code : "request_failed";
    error.guidance = typeof data.next_step === "string" ? data.next_step : "";
    throw error;
  }
  return data;
}
function setLoad(active) {
  state.busy = active;
  $("refresh").disabled = !state.current || active;
  $("explain").disabled = active || !state.evidence || state.workflow.evidence!=="retrieved";
  $("plan").disabled = active || !state.evidence || state.workflow.evidence!=="retrieved";
  $("save-review").disabled = active || !state.evidence || state.workflow.evidence!=="retrieved" || !state.evidence.exceptions.length;
}
function navigateSection(sectionId) {
  if (!state.evidence) return;
  const target=$(sectionId);
  if (!target || target.hidden) return;
  target.scrollIntoView({ behavior:"smooth", block:"start" });
  target.setAttribute("tabindex","-1");
  target.focus({ preventScroll:true });
}
function renderJourney() {
  const wf=state.workflow;
  const hasEvidence=wf.evidence==="retrieved";
  const noFindings=hasEvidence && state.evidence.exceptions.length===0;
  const explanationReady=wf.explain==="accepted" || wf.explain==="no_findings";
  const planReady=wf.plan==="accepted";
  const agentRejected=wf.explain==="rejected" || wf.plan==="rejected";
  const anyRunning=wf.explain==="running" || wf.plan==="running";

  const impaired=hasEvidence && state.evidence.source_checks.some(check=>
    !["available","not_found"].includes(check.status));
  $("step-evidence").textContent=wf.evidence==="retrieved"?
    (impaired?"Partial source access":"Source checks retrieved"):wf.evidence==="loading"?"Retrieving…":
    wf.evidence==="failed"?"Source read failed":wf.evidence==="stale"?"Outdated snapshot":"Not checked";
  $("step-agents").textContent=agentRejected?"Rejected output · manual review":
    anyRunning?"Generating…":explanationReady && planReady?"Both accepted":
    (explanationReady||planReady)?"Partially generated":"Not requested";
  $("step-review").textContent=noFindings?"No cited finding to annotate":
    wf.reviewCount<0?"History unavailable":
    wf.reviewCount>0?wf.reviewCount+" local note"+(wf.reviewCount===1?"":"s"):"No local note";
  $("step-audit").textContent=wf.audit==="available"?"Persisted events viewed":
    wf.audit==="empty"?"No archived events":wf.audit==="unavailable"?
    "Unavailable · no substitute":wf.audit==="loading"?"Reading…":"Not checked";

  for(const control of document.querySelectorAll("[data-journey-target]")){
    control.disabled=!hasEvidence;
  }
  const button=$("journey-continue");
  button.disabled=!hasEvidence;
  let target="agent-investigation";
  let labelText="Go to agent tools →";
  let summary="Evidence retrieved. Agents are optional and require explicit clicks.";
  if (!hasEvidence){
    summary=wf.evidence==="stale"?"Evidence changed since retrieval. Refresh before requesting agents or recording notes.":
      wf.evidence==="failed"?
      "Source validation failed. Refresh evidence before attempting AI or recording notes.":
      wf.evidence==="loading"?"Retrieving and validating this synthetic case…":
      "Choose a case to retrieve real synthetic source evidence. No model request runs automatically.";
    labelText=wf.evidence==="stale"?"Refresh evidence first":"Choose a case";
  }else if(agentRejected){
    summary="An AI output was rejected. It was not accepted as evidence or a completed investigation; retry only deliberately.";
    labelText="Inspect agent failure →";
  }else if (anyRunning){
    summary="A hosted model request is running. No proposed source checks are being executed.";
    labelText="Inspect agent progress →";
  }else if (!explanationReady || !planReady){
    summary=impaired?
      "At least one source query was unavailable. Treat document absence as unknown; agent output cannot certify a complete snapshot.":
      noFindings?
      "No rule-based discrepancy was found in this source snapshot; this does not establish completeness. You can inspect the bounded no-finding agent path.":
      "CareFlow findings are ready. Ask CaseLens and NextStep explicitly; their results are independently validated.";
  }else if (!noFindings && wf.reviewCount===0){
    target="review-panel";
    labelText="Go to local review →";
    summary="Both agent outputs were accepted. You can write a fictional, non-clinical note against a cited CareFlow finding.";
  }else{
    target="meterless-audit";
    labelText="Inspect event history →";
    summary=wf.reviewCount>0?
      "Local note recorded, not an approval. The Meterless event history is a separate read-only store.":
      wf.reviewCount<0?"Review history could not be verified. Inspect locally, then view the separate Meterless audit.":
      "No finding is available for a cited local note. Inspect genuine archived events, if previously persisted.";
  }
  $("journey-summary").textContent=summary;
  button.textContent=labelText;
  button.dataset.target=target;
  document.querySelectorAll(".journey-step").forEach((control)=>{
    control.classList.toggle("is-ready",hasEvidence);
    let active=false;
    if(control.dataset.journeyTarget==="findings-card")active=hasEvidence;
    if(control.dataset.journeyTarget==="agent-investigation")active=explanationReady || planReady;
    if(control.dataset.journeyTarget==="review-panel")active=wf.reviewCount>0;
    if(control.dataset.journeyTarget==="meterless-audit")active=wf.audit==="available";
    control.classList.toggle("is-done",active);
  });
}
function resetWorkflow(){
  state.workflow={
    evidence:"loading", explain:"not_requested", plan:"not_requested",
    reviewCount:0, audit:"not_checked",
  };
  renderJourney();
}
function renderList() {
  const q = $("case-search").value.trim().toLowerCase();
  const matches = state.ids.filter((x) => x.toLowerCase().includes(q));
  clear("case-list");
  $("case-count").textContent=String(matches.length)+"/"+String(state.ids.length);
  if (!matches.length) {
    $("case-list").append(el("p","loading-list","No matching synthetic case IDs"));
    return;
  }
  for (const id of matches) {
    const btn = el("button",state.current === id ? "active" : "");
    btn.type = "button";
    btn.setAttribute("aria-current",state.current === id ? "page" : "false");
    const inspected=state.inspected.get(id);
    const noteCount=state.localNotes.get(id) || 0;
    const right=el("span","case-summary");
    if(inspected){
      if(inspected.stale){
        right.append(el("span","case-label uninspected","Stale · refresh"));
      }else{
      right.append(el("span",inspected.findings?"case-label flagged":"case-label inspected",
        inspected.findings?inspected.findings+" finding"+(inspected.findings===1?"":"s"):
        inspected.impaired?"Partial read":"Read"));
      if(inspected.impaired && inspected.findings)
        right.append(el("span","case-label uninspected","Partial"));
      }
    }else{
      right.append(el("span","case-label uninspected","Not checked"));
    }
    if(noteCount)right.append(el("span","note-mark","Note "+noteCount));
    btn.append(el("span","case-id",id),right);
    btn.setAttribute("aria-label",id+": "+(inspected?
      inspected.findings+" finding(s) observed in session":"sources not checked in session")+
      (noteCount?", "+noteCount+" local notes":""));
    btn.addEventListener("click",() => loadCase(id));
    $("case-list").append(btn);
  }
}
function chip(text, style) { return el("span","chip " + (style || ""),text); }
function refs(target, ids) {
  const wrap=el("div","refs");
  for (const id of ids) {
    const btn=el("button","ref",id);
    btn.type="button";
    btn.setAttribute("aria-label","Show evidence " + id);
    btn.addEventListener("click",()=> {
      const row=[...document.querySelectorAll("#timeline tr")].find(
        (item) => item.dataset.record === id);
      if (!row) return;
      row.scrollIntoView({behavior:"smooth",block:"center"});
      row.classList.add("highlight");
      setTimeout(()=>row.classList.remove("highlight"),1300);
    });
    wrap.append(btn);
  }
  target.append(wrap);
}
function renderFindings(bundle) {
  clear("findings");
  if (!bundle.exceptions.length) {
    $("findings").append(el("p","", "No rule-based administrative exceptions in this retrieved snapshot. This does not certify source completeness or clinical outcomes."));
    return;
  }
  for (const issue of bundle.exceptions) {
    const card=el("div","finding");
    card.append(el("h3","",label(issue.category)));
    card.append(el("p","",issue.description));
    refs(card,issue.evidence_record_ids || []);
    $("findings").append(card);
  }
}
function renderSources(bundle) {
  clear("sources");
  const recent={};
  for(const source of bundle.source_checks) {
    if (!recent[source.source_system] || source.attempt > recent[source.source_system].attempt)
      recent[source.source_system]=source;
  }
  for(const source of SOURCE_NAMES) {
    const status=recent[source]?.status || "not_checked";
    const cls=status==="available"?"ok":status==="not_found"?"warn":"bad";
    const row=el("div","source-row");
    const left=el("div","source-left");
    left.append(el("span","source-indicator "+cls),el("span","",label(source)));
    row.append(left,chip(status,cls));
    $("sources").append(row);
  }
}
function timeString(text) {
  const date=new Date(text);
  return Number.isNaN(date.getTime())? "Unknown UTC time" :
    date.toISOString().replace("T"," ").slice(0,16)+" UTC";
}
function renderTimeline(bundle) {
  clear("timeline");
  const entries=[...bundle.observations].sort((a,b)=>
    a.observed_at.localeCompare(b.observed_at));
  $("timeline-count").textContent=entries.length+" events";
  for(const record of entries) {
    const tr=el("tr");
    tr.dataset.record=record.record_id;
    for (const value of [
      timeString(record.observed_at),label(record.record_type),
      record.record_id,record.source_record_id,record.subject_ref
    ]) {
      const td=el("td");
      if([record.record_id,record.source_record_id,record.subject_ref].includes(value))
        td.append(el("code","",value));
      else td.textContent=value;
      tr.append(td);
    }
    $("timeline").append(tr);
  }
}
const dispositionNames = {
  "request_source_verification":"Source verification proposed",
  "escalate_admin_review":"Administrative escalation proposed",
  "reviewed_unresolved":"Reviewed; unresolved",
};
function prepareReviewForm(bundle) {
  $("review-form").reset();
  $("reviewer-label").value="DEMO-REVIEWER";
  $("review-confirm").checked=false;
  $("review-status").textContent="";
  state.reviewRequestId=null;
  clear("review-finding");
  for(const [index,issue] of bundle.exceptions.entries()){
    const option=el("option","",String(index+1)+". "+label(issue.category)+
      " ("+issue.evidence_record_ids.join(", ")+")");
    option.value=String(index);
    $("review-finding").append(option);
  }
  if(!bundle.exceptions.length){
    $("review-status").textContent="No CareFlow finding available for a cited administrative review note.";
    $("save-review").disabled=true;
  }
}
function renderReviewHistory(data) {
  clear("review-history");
  const reviews=data.reviews || [];
  $("stat-reviews").textContent=reviews.length?String(reviews.length):"None";
  state.workflow.reviewCount=reviews.length;
  state.localNotes.set(state.current,reviews.length);
  renderJourney();
  renderList();
  $("review-total").textContent=reviews.length+" events";
  if(!reviews.length){
    $("review-history").append(el("p","empty-history","No local notes recorded for this case."));
    return;
  }
  for(const entry of [...reviews].reverse()){
    const box=el("div","history-entry");
    const row=el("div","history-header");
    row.append(el("strong","",dispositionNames[entry.disposition] || "Administrative note"),
      el("span","history-time",timeString(entry.recorded_at_utc)));
    box.append(row);
    box.append(el("p","",entry.note));
    box.append(el("div","history-meta","Tag: "+entry.reviewer_label+" · "+label(entry.finding_category)+
      " · Snapshot "+entry.evidence_snapshot_sha256.slice(0,10)+"…"));
    refs(box,entry.evidence_record_ids);
    $("review-history").append(box);
  }
}
const ACTIVITY_STATES = Object.freeze({
  requested:"Requested",
  retrieving_evidence:"Reading verified evidence",
  waiting_for_model:"Waiting for hosted model",
  validating:"Validating model response",
  no_model_needed:"No model inference needed",
  accepted:"Validated and accepted",
  rejected:"Output rejected",
  failed:"Operation failed",
  stale_evidence:"Evidence changed · refresh required",
  awaiting_human_review:"Human review required",
  review_note_recorded:"Fictional administrative note recorded",
});
const ACTIVITY_OPERATIONS = Object.freeze({
  careflow:"CareFlow", caselens:"CaseLens", nextstep:"NextStep", review:"Local review",
});
const IMPORTANT_ACTIVITY = new Set([
  "accepted","rejected","failed","stale_evidence",
  "awaiting_human_review","review_note_recorded"
]);
function renderAttentionCount(){
  $("activity-unread").textContent=state.activityUnread.size+" new";
}
function renderActivity(data) {
  clear("activity-feed");
  const events=data.events || [];
  const previous=state.activitySeen.get(data.case_id);
  const prior = previous || new Set(events.map(e=>e.event_id));
  const fresh=events.filter(e=>!prior.has(e.event_id));
  state.activitySeen.set(data.case_id,new Set([...prior,...events.map(e=>e.event_id)]));
  // Notify on new *server-stored* events only, never on client guesses.
  for(const event of fresh) {
    if(IMPORTANT_ACTIVITY.has(event.state)){
      state.activityUnread.add(event.event_id);
      $("activity-toast").textContent=
        (ACTIVITY_OPERATIONS[event.operation]||"Agent")+" — "+
        (ACTIVITY_STATES[event.state]||"Activity changed")+
        " · "+data.case_id+".";
    }
  }
  renderAttentionCount();
  // Update only in-flight status labels from actually persisted server
  // checkpoints. Terminal acceptance/rejection remains owned by the
  // response validator and the explicit invokeAgent() result.
  for(const [kind,operation,statusId] of [
    ["explain","caselens","explain-status"],
    ["plan","nextstep","plan-status"],
  ]){
    if(state.workflow[kind]!=="running")continue;
    const latest=[...events].reverse().find(e=>e.operation===operation);
    if(latest && ["retrieving_evidence","waiting_for_model","validating"].includes(latest.state)){
      $(statusId).textContent=(ACTIVITY_STATES[latest.state]||"Processing")+
        " · Observed server checkpoint";
    }
  }
  $("activity-status").textContent=data.total?
    data.total+" recorded checkpoints · "+(data.truncated?"Latest 100 shown":"Current synthetic case")+
    " · In-app only":
    "No server activity recorded for this case.";
  for(const event of [...events].reverse().slice(0,16)){
    const div=el("div","activity-entry");
    div.dataset.state=event.state;
    const head=el("div","activity-entry-head");
    head.append(
      el("strong","",ACTIVITY_OPERATIONS[event.operation]||"Application"),
      el("span","",ACTIVITY_STATES[event.state]||"Observed event")
    );
    div.append(head);
    div.append(el("div","activity-entry-time",timeString(event.occurred_at_utc)));
    $("activity-feed").append(div);
  }
  if(!events.length)$("activity-feed").append(
    el("p","activity-none","A future request will appear after the server actually receives it.")
  );
}
async function refreshActivity(caseId,token){
  if(state.activityPending || !caseId)return;
  state.activityPending=true;
  try{
    const response=await request("/api/cases/"+encodeURIComponent(caseId)+"/activity");
    if(token!==state.generation || state.current!==caseId)return;
    renderActivity(response);
  }catch(error){
    if(token!==state.generation || state.current!==caseId)return;
    $("activity-status").textContent="Activity history unavailable ["+
      (error.code||"request_failed")+"]; progress cannot be verified.";
  }finally{
    state.activityPending=false;
  }
}
async function loadReviewHistory(id,token){
  try{
    const data=await request("/api/cases/"+encodeURIComponent(id)+"/reviews");
    if(token!==state.generation)return;
    renderReviewHistory(data);
  }catch(error){
    if(token!==state.generation)return;
    $("review-history").replaceChildren(el("p","review-error","Could not load local review history: "+error.message));
    state.workflow.reviewCount=-1;
    renderJourney();
  }
}
async function loadReviewActivity(){
  try{
    const data=await request("/api/review-activity");
    clear("review-activity");
    $("activity-count").textContent=data.activity.length;
    for(const item of data.activity)state.localNotes.set(item.case_id,item.recorded_notes);
    renderList();
    if(!data.activity.length){
      $("review-activity").append(el("p","", "None recorded yet"));
      return;
    }
    for(const item of data.activity){
      const btn=el("button","activity-item",item.case_id+" · "+item.recorded_notes+" notes");
      btn.type="button";
      btn.addEventListener("click",()=>loadCase(item.case_id));
      $("review-activity").append(btn);
    }
  }catch(error){
    $("review-activity").replaceChildren(el("p","", "Review activity unavailable"));
  }
}
async function submitReview(event){
  event.preventDefault();
  if(!state.evidence || !state.current || state.busy || state.workflow.evidence!=="retrieved" || !state.evidence.exceptions.length)return;
  if(!$("review-form").reportValidity())return;
  const caseId=state.current;
  const token=state.generation;
  const index=Number($("review-finding").value);
  const issue=state.evidence.exceptions[index];
  if(!issue)return;
  if(!state.reviewRequestId) state.reviewRequestId=crypto.randomUUID();
  const draft={
    finding_index:index,
    finding_category:issue.category,
    evidence_record_ids:issue.evidence_record_ids,
    evidence_snapshot_sha256:state.evidence.evidence_snapshot_sha256,
    reviewer_label:$("reviewer-label").value.trim(),
    disposition:$("review-disposition").value,
    note:$("review-note").value.trim(),
    request_id:state.reviewRequestId,
  };
  setLoad(true);
  $("review-status").textContent="Revalidating source snapshot and recording local note…";
  try {
    const saved=await request("/api/cases/"+encodeURIComponent(caseId)+"/reviews",{
      method:"POST",
      headers:{"Content-Type":"application/json",
        "X-TBCareOS-Review-Intent":"record-human-admin-review-v1"},
      body:JSON.stringify(draft),
    });
    if(token!==state.generation)return;
    $("review-status").textContent="Recorded "+saved.review_event_id+
      ". This is a local administrative note, not an approval or external action.";
    $("review-confirm").checked=false;
    $("review-note").value="";
    state.reviewRequestId=null;
    await loadReviewHistory(caseId,token);
    await loadReviewActivity();
    refreshActivity(caseId,token);
  }catch(error){
    if(token!==state.generation)return;
    $("review-status").textContent="Not recorded ["+(error.code||"request_failed")+"]: "+error.message+
      (error.guidance?" "+error.guidance:"");
    // Retain request ID for safe idempotent retry; changing the draft
    // resets the ID through input/change listeners.
  }finally{if(token===state.generation)setLoad(false);}
}
function renderAuditReport(report) {
  $("audit-status").textContent=report.has_persisted_events?
    "Verified local Meterless World Model event index · "+report.namespace:
    "No previously archived Meterless event history for this case.";
  $("audit-body").hidden=!report.has_persisted_events;
  $("audit-event-count").textContent=String(report.event_count);
  $("audit-entry-count").textContent=String(report.audit_count);
  $("audit-visible-count").textContent=String(report.events.length);
  clear("audit-event-list");
  if(!report.has_persisted_events)return;
  for(const event of [...report.events].reverse()){
    const card=el("div","audit-event");
    const row=el("div","audit-event-head");
    row.append(el("span","audit-event-id",event.event_id),
      el("span","audit-event-kind",event.event_type));
    card.append(row,el("div","audit-event-date",timeString(event.event_at)));
    $("audit-event-list").append(card);
  }
  $("audit-truncation").textContent=report.truncated?
    "Showing the latest "+report.events.length+" of "+report.event_count+" persisted events.":
    "All "+report.event_count+" persisted events are displayed. No follow-up source queries or reviewer actions were executed by this audit viewer.";
}
async function loadMeterlessAudit(id,token) {
  $("audit-body").hidden=true;
  state.workflow.audit="loading";
  renderJourney();
  $("audit-status").textContent="Reading actual local Meterless event history…";
  try {
    const data=await request("/api/cases/"+encodeURIComponent(id)+"/audit");
    if(token!==state.generation)return;
    renderAuditReport(data);
    state.workflow.audit=data.has_persisted_events?"available":"empty";
    renderJourney();
  }catch(error){
    if(token!==state.generation)return;
    $("audit-status").textContent="Audit unavailable ["+(error.code||"request_failed")+
      "]: "+error.message+(error.guidance?" "+error.guidance:"")+
      " No events have been invented.";
    $("audit-body").hidden=true;
    state.workflow.audit="unavailable";
    renderJourney();
  }
}
async function loadCase(id) {
  const token=++state.generation;
  state.current=id;
  state.activityUnread.clear();
  renderAttentionCount();
  $("activity-status").textContent="Reading server-observed activity…";
  clear("activity-feed");
  state.evidence=null;
  state.reviewRequestId=null;
  resetWorkflow();
  renderList();
  document.querySelectorAll("[data-demo-case]").forEach(btn=>{
    const selected=btn.dataset.demoCase===id;
    btn.classList.toggle("active",selected);
    btn.setAttribute("aria-pressed",String(selected));
  });
  hideError();
  $("case-title").textContent=id;
  $("crumb-case").textContent=id;
  $("case-subtitle").textContent="Retrieving source-linked synthetic administrative records…";
  $("case-content").hidden=true;
  $("content-empty").hidden=false;
  $("content-empty").replaceChildren(el("p","", "Retrieving read-only evidence…"));
  setLoad(true);
  try {
    const bundle=await request("/api/cases/"+encodeURIComponent(id)+"/evidence");
    if(token!==state.generation)return;
    state.evidence=bundle;
    state.workflow.evidence="retrieved";
    state.workflow.reviewCount=-1;
    const impaired=bundle.source_checks.some(check=>
      !["available","not_found"].includes(check.status));
    state.inspected.set(id,{
      findings:bundle.exceptions.length, observations:bundle.observations.length, impaired
    });
    renderJourney();
    renderList();
    $("case-subtitle").textContent="Synthetic administrative case · Source observations and bounded review";
    $("stat-evidence").textContent=bundle.observations.length;
    $("stat-checks").textContent=bundle.source_checks.length;
    $("stat-findings").textContent=bundle.exceptions.length;
    renderFindings(bundle);
    renderSources(bundle);
    renderTimeline(bundle);
    prepareReviewForm(bundle);
    await loadReviewHistory(id,token);
    if(token!==state.generation)return;
    $("content-empty").hidden=true;
    loadMeterlessAudit(id,token);
    $("case-content").hidden=false;
    refreshActivity(id,token);
    clear("explanation");clear("plan-result");
    $("explain-status").textContent="Not requested";
    $("plan-status").textContent="Not requested";
    $("explain-status").dataset.state="idle";
    $("plan-status").dataset.state="idle";
  } catch(error) {
    if(token!==state.generation)return;
    showError("Evidence retrieval failed. "+error.message+" Do not interpret this as missing care.");
    $("content-empty").replaceChildren(el("p","", "Source evidence could not be verified."));
    $("case-subtitle").textContent="Retrieval unsuccessful";
    state.workflow.evidence="failed";
    renderJourney();
  } finally {
    if(token===state.generation)setLoad(false);
  }
}
function renderExplanation(report) {
  clear("explanation");
  if(!report.hypotheses?.length) {
    $("explanation").append(el("p","", "No CareFlow findings required explanation in this snapshot."));
    return;
  }
  for(const hypothesis of report.hypotheses) {
    const block=el("div","result-item");
    block.append(el("strong","",hypothesis.hypothesis),chip(hypothesis.assessment,"warn"));
    block.append(el("p","",hypothesis.reason));
    refs(block,hypothesis.evidence_record_ids);
    $("explanation").append(block);
  }
  if(report.unresolved_questions?.length) {
    const q=el("div","result-item");
    q.append(el("strong","", "Questions for human review"));
    for(const question of report.unresolved_questions)q.append(el("p","",question));
    $("explanation").append(q);
  }
}
function renderPlan(report) {
  clear("plan-result");
  for(const [i,action] of report.actions.entries()) {
    const block=el("div","result-item");
    const actionText=action.action==="read_only_source_query"?
      "Proposed check — not executed":action.action==="manual_review"?
      "Human review required":"Stop / no automatic follow-up";
    block.append(el("strong","",String(i+1)+". "+actionText));
    if(action.source_system)block.append(chip(action.source_system,""));
    block.append(el("p","",action.reason));
    refs(block,action.evidence_record_ids || []);
    $("plan-result").append(block);
  }
}
function renderAgentFailure(kind, error) {
  const container=kind==="explain"?"explanation":"plan-result";
  clear(container);
  const title=kind==="explain"?"No explanation accepted":"No verification plan accepted";
  const card=el("div","agent-failure");
  const headline=el("div","agent-failure-heading");
  headline.append(el("span","agent-failure-icon","!"),el("strong","",title));
  card.append(headline);

  const code=String(error.code || "request_failed");
  const description=code==="nvidia_incomplete_response" ?
    "The hosted model did not provide a complete usable answer.":
    code==="caselens_structure"||code==="caselens_invalid_json" ?
    "The response did not follow the required explanation format.":
    code.startsWith("caselens_")||code==="agent_validation_rejected" ?
    "The response did not pass our independent evidence or safety checks.":
    code==="nvidia_rate_limited"?"The provider is rate limiting requests.":
    code==="nvidia_key_missing"||code==="nvidia_access_denied" ?
    "Model access is unavailable in this local server session.":
    "The requested hosted inference could not be verified.";
  card.append(el("p","agent-failure-summary",description));
  card.append(el("p","agent-failure-context",
    "The source evidence remains available. No unsupported model result was accepted. No substitute result was generated. No verification query was executed."));
  const support=el("p","agent-failure-guidance");
  support.textContent=error.guidance || "Review the source-linked findings before deciding whether to retry.";
  card.append(support);

  const controls=el("div","agent-failure-controls");
  const inspect=el("button","button secondary","View retrieved findings");
  inspect.type="button";
  inspect.addEventListener("click",()=>navigateSection("findings-card"));
  controls.append(inspect);
  if(!["nvidia_key_missing","nvidia_access_denied","nvidia_model_unavailable"].includes(code)){
    const retry=el("button","button primary",
      kind==="explain"?"Retry CaseLens explicitly":"Retry NextStep explicitly");
    retry.type="button";
    retry.addEventListener("click",()=>invokeAgent(kind));
    controls.append(retry);
  }
  card.append(controls);
  if(kind==="explain"){
    card.append(el("p","agent-failure-note",
      "NextStep may still return an independently validated read-only plan; that does not count as a successful full explanation-and-plan workflow."));
  }
  $(container).append(card);
}
async function invokeAgent(kind) {
  if(!state.current || !state.evidence || state.busy || state.workflow.evidence!=="retrieved")return;
  const caseId=state.current;
  const token=state.generation;
  const statusId=kind==="explain"?"explain-status":"plan-status";
  const actionName=kind==="explain"?"CaseLens":"NextStep";
  const containerId=kind==="explain"?"explanation":"plan-result";
  clear(containerId);
  $(statusId).textContent="Running "+actionName+" with hosted Nemotron…";
  $(statusId).dataset.state="running";
  state.workflow[kind==="explain"?"explain":"plan"]="running";
  renderJourney();
  setLoad(true);
  try{
    const result=await request("/api/cases/"+encodeURIComponent(caseId)+"/"+kind,
      {method:"POST",headers:{"X-TBCareOS-Evidence-SHA256":state.evidence.evidence_snapshot_sha256}});
    if(token!==state.generation)return;
    if(kind==="explain")renderExplanation(result);
    else renderPlan(result);
    const noFinding=kind==="explain" && result.hypotheses.length===0;
    const noPlanModel=kind==="plan" && state.evidence.exceptions.length===0;
    $(statusId).textContent=noFinding?
      "No CareFlow finding · no model call required · human review remains":
      noPlanModel?"Bounded review/stop plan · no model call required":
      "Accepted · Bounded agent output · Human review required";
    $(statusId).dataset.state="accepted";
    state.workflow[kind==="explain"?"explain":"plan"]=noFinding?"no_findings":"accepted";
    renderJourney();
    refreshActivity(caseId,token);
  } catch(error){
    if(token!==state.generation)return;
    if(error.code==="evidence_snapshot_changed"){
      // Both agent outputs are invalidated for the old evidence snapshot.
      state.workflow.evidence="stale";
      const inspected=state.inspected.get(caseId);
      if(inspected)inspected.stale=true;
      renderList();
      state.workflow.explain="not_requested";
      state.workflow.plan="not_requested";
      clear("explanation");clear("plan-result");
      $("explain-status").textContent="Outdated source snapshot · refresh evidence";
      $("plan-status").textContent="Outdated source snapshot · refresh evidence";
      $("explain-status").dataset.state="rejected";
      $("plan-status").dataset.state="rejected";
      showError("Evidence changed since this case was opened. Refresh evidence before another agent request or local review note.");
      renderJourney();
      refreshActivity(caseId,token);
      return;
    }
    $(statusId).textContent="Not accepted · "+String(error.code || "request_failed");
    renderAgentFailure(kind,error);
    refreshActivity(caseId,token);
    $(statusId).dataset.state="rejected";
    state.workflow[kind==="explain"?"explain":"plan"]="rejected";
    renderJourney();
  } finally { if(token===state.generation)setLoad(false); }
}
async function init(){
  $("case-search").addEventListener("input",renderList);
  $("activity-mark-seen").addEventListener("click",()=>{
    state.activityUnread.clear();
    renderAttentionCount();
    $("activity-toast").textContent="Recent in-app activity marked noticed.";
  });
  // Poll only while the browser is open and visible. This is not a worker
  // or a subscription that delivers after the tab/server closes.
  window.setInterval(()=>{
    if(document.visibilityState==="visible" && state.current)
      refreshActivity(state.current,state.generation);
  },2000);
  document.querySelectorAll("[data-demo-case]").forEach(btn=>btn.addEventListener("click",()=>{
    if(state.ids.includes(btn.dataset.demoCase))loadCase(btn.dataset.demoCase);
  }));
  document.querySelectorAll("[data-journey-target]").forEach(btn=>btn.addEventListener("click",()=>navigateSection(btn.dataset.journeyTarget)));
  $("journey-continue").addEventListener("click",()=>navigateSection($("journey-continue").dataset.target));
  renderJourney();
  $("refresh").addEventListener("click",()=>state.current&&loadCase(state.current));
  $("explain").addEventListener("click",()=>invokeAgent("explain"));
  $("plan").addEventListener("click",()=>invokeAgent("plan"));
  $("review-form").addEventListener("submit",submitReview);
  $("reload-audit").addEventListener("click",()=>state.current && loadMeterlessAudit(state.current,state.generation));
  for(const id of ["review-finding","review-disposition","reviewer-label","review-note"]){
    $(id).addEventListener("input",()=>{state.reviewRequestId=null;});
    $(id).addEventListener("change",()=>{state.reviewRequestId=null;});
  }
  try {
    const manifest=await request("/api/cases");
    state.ids=manifest.cases.map(x=>x.case_id);
    state.sourceMode=manifest.source_mode;
    document.querySelectorAll("[data-demo-case]").forEach(btn=>{
      btn.disabled=!state.ids.includes(btn.dataset.demoCase);
      btn.title=btn.disabled?"Not available in this demo mode":"Retrieve this synthetic case";
    });
    $("source-mode").textContent=manifest.source_mode==="saved_fixture"?
      "Saved synthetic fixture":"Local Zetaris connector";
    $("case-count").textContent=state.ids.length;
    renderList();
    loadReviewActivity();
    if(state.ids.includes("CASE-TB-018"))loadCase("CASE-TB-018");
  }catch(error){
    showError("Could not load the synthetic case inventory. "+error.message);
    $("case-list").replaceChildren(el("p","loading-list","Connection failed"));
  }
}
init();
