/* TB-CareOS local product MVP. Render untrusted evidence with textContent only. */
"use strict";
const $ = (id) => document.getElementById(id);
const state = { ids: [], current: null, evidence: null, generation: 0, busy: false };
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
  if (!response.ok) throw new Error(data.error || "Request did not complete.");
  return data;
}
function setLoad(active) {
  state.busy = active;
  $("refresh").disabled = !state.current || active;
  $("explain").disabled = active;
  $("plan").disabled = active;
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
async function loadCase(id) {
  const token=++state.generation;
  state.current=id;
  state.evidence=null;
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
    $("content-empty").hidden=true;
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
    $(statusId).textContent="Failed · "+error.message+" No substitute result was generated.";
    $(containerId).append(el("p","", "The model/source invocation failed. No outcome can be inferred."));
  } finally { if(token===state.generation)setLoad(false); }
}
async function init(){
  $("case-search").addEventListener("input",renderList);
  $("refresh").addEventListener("click",()=>state.current&&loadCase(state.current));
  $("explain").addEventListener("click",()=>invokeAgent("explain"));
  $("plan").addEventListener("click",()=>invokeAgent("plan"));
  try {
    const manifest=await request("/api/cases");
    state.ids=manifest.cases.map(x=>x.case_id);
    $("source-mode").textContent=manifest.source_mode==="saved_fixture"?
      "Saved synthetic fixture":"Local Zetaris connector";
    $("case-count").textContent=state.ids.length;
    renderList();
    if(state.ids.includes("CASE-TB-018"))loadCase("CASE-TB-018");
  }catch(error){
    showError("Could not load the synthetic case inventory. "+error.message);
    $("case-list").replaceChildren(el("p","loading-list","Connection failed"));
  }
}
init();
