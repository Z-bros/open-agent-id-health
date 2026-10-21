# Candidate 3: TB-NextStep — adaptive bounded investigation

**User:** coordinator resolving uncertain administrative evidence.  
**Problem:** Unbounded retries waste work and can mistake temporary outage for nonexistent records.  
**Unique behavior:** planner/critic decides read-only next permitted evidence query, constrained by retry budget, permission, evidence gain and mandatory safe stop/escalation.  
**Standalone input:** saved `evidence_bundle.v1` plus optional `explanation_report.v1`. **Output:** `verification_plan.v1`.  
**Evaluate:** useful queries per resolved case, transient-recovery success, no policy violations, correct escalation.

**21 Oct status:** planning and CLI placeholder only. Official track identifier/name **not verified**.
