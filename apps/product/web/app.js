/* TB-CareOS local product MVP. Render untrusted evidence with textContent only. */
"use strict";
const $ = (id) => document.getElementById(id);
const state = { ids: [], current: null, evidence: null, generation: 0, busy: false, reviewRequestId: null };
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
  $("explain").disabled = active;
  $("plan").disabled = active;
  $("save-review").disabled = active || !state.evidence || !state.evidence.exceptions.length;
}
function renderList() {
  const q = $("case-search").value.trim().toLowerCase();
  const matches = state.ids.filter((x) => x.toLowerCase().includes(q));
  clear("case-list");
  if (!matches.length) {
    $("case-list").append(el("p","loading-list","No matching synthetic case IDs"));
    return;
  }
  for (const id of matches) {
    const btn = el("button",state.current === id ? "active" : "");
    btn.type = "button";
    btn.setAttribute("aria-current",state.current === id ? "page" : "false");
    btn.append(el("span","",id), el("span","case-mark"));
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
async function loadReviewHistory(id,token){
  try{
    const data=await request("/api/cases/"+encodeURIComponent(id)+"/reviews");
    if(token!==state.generation)return;
    renderReviewHistory(data);
  }catch(error){
    if(token!==state.generation)return;
    $("review-history").replaceChildren(el("p","review-error","Could not load local review history: "+error.message));
  }
}
async function loadReviewActivity(){
  try{
    const data=await request("/api/review-activity");
    clear("review-activity");
    $("activity-count").textContent=data.activity.length;
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
  if(!state.evidence || !state.current || state.busy || !state.evidence.exceptions.length)return;
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
  $("audit-status").textContent="Reading actual local Meterless event history…";
  try {
    const data=await request("/api/cases/"+encodeURIComponent(id)+"/audit");
    if(token!==state.generation)return;
    renderAuditReport(data);
  }catch(error){
    if(token!==state.generation)return;
    $("audit-status").textContent="Audit unavailable ["+(error.code||"request_failed")+
      "]: "+error.message+(error.guidance?" "+error.guidance:"")+
      " No events have been invented.";
    $("audit-body").hidden=true;
  }
}
async function loadCase(id) {
  const token=++state.generation;
  state.current=id;
  state.evidence=null;
  state.reviewRequestId=null;
  renderList();
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
    clear("explanation");clear("plan-result");
    $("explain-status").textContent="Not requested";
    $("plan-status").textContent="Not requested";
  } catch(error) {
    if(token!==state.generation)return;
    showError("Evidence retrieval failed. "+error.message+" Do not interpret this as missing care.");
    $("content-empty").replaceChildren(el("p","", "Source evidence could not be verified."));
    $("case-subtitle").textContent="Retrieval unsuccessful";
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
async function invokeAgent(kind) {
  if(!state.current || !state.evidence || state.busy)return;
  const caseId=state.current;
  const token=state.generation;
  const statusId=kind==="explain"?"explain-status":"plan-status";
  const actionName=kind==="explain"?"CaseLens":"NextStep";
  const containerId=kind==="explain"?"explanation":"plan-result";
  clear(containerId);
  $(statusId).textContent="Running "+actionName+" with hosted Nemotron…";
  setLoad(true);
  try{
    const result=await request("/api/cases/"+encodeURIComponent(caseId)+"/"+kind,
      {method:"POST"});
    if(token!==state.generation)return;
    if(kind==="explain")renderExplanation(result);
    else renderPlan(result);
    $(statusId).textContent="Completed · Human review required";
  } catch(error){
    if(token!==state.generation)return;
    $(statusId).textContent="Failed ["+(error.code || "request_failed")+"] · "+error.message+
      (error.guidance ? " "+error.guidance : "")+" No substitute result was generated.";
    $(containerId).append(el("p","", "The model/source invocation failed. No outcome can be inferred."));
  } finally { if(token===state.generation)setLoad(false); }
}
async function init(){
  $("case-search").addEventListener("input",renderList);
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
