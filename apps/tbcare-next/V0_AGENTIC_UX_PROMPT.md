# v0 Follow-up Prompt: TB-CareOS Agentic Activity Experience

Use the attached TB-CareOS Next.js project as the source of truth. **Refine the existing working React implementation**, especially `app/components/AgentActivity.tsx` and `app/page.tsx`, without removing existing integrations or rebuilding the site from screenshots.

## Agent-activity UX to refine

**1. Intent and thinking states**
- Add/keep a clear intent strip for **Inspect → Explain → Propose → Human Review**, reflecting operations a reviewer chooses and observable client states.
- For each independent agent, show `not_requested`, `running`, `accepted`, `rejected`, and the no-finding/no-hosted-model path. During processing show a calm, progressive UI for **request explicitly initiated → waiting for backend-validated output → accepted/rejected response**.
- These are request lifecycle states; do NOT invent internal reasoning steps, hidden chain-of-thought, streaming tokens, tool calls or completion percentages not returned by the server.
- In a failure show safe error code, View cited evidence, and **explicit retry**. A CaseLens failure must not be hidden by NextStep success. UI outcomes in demo mode must always be labeled simulated.

**2. Human in the loop**
- Keep a prominent checkpoint where the reviewer can inspect cited evidence IDs and source types, acknowledge that proposals are NOT EXECUTED, and then open the existing local-note form.
- Require both evidence-checked and scope-acknowledged checkboxes plus the existing final confirmation before enabling **Record local note**. Reset acknowledgments when a case or evidence snapshot changes.
- Never label a recorded note as official approval, an external escalation, resolution of a case, diagnosis, treatment, or authorization to execute proposals.

**3. Asynchronous feedback and notifications**
- Keep a notification bell and session-level activity center with unread count, mark-read/clear controls, contextual notifications, and compact nonintrusive toasts.
- Notify on actual local user-initiated request completion/failure, evidence staleness, reviewer-note saving, and genuine audit-read availability or error. Never invent events from Meterless.
- Optional browser notifications must remain **opt-in** and only fire for a task already requested in this open tab when the browser is hidden. No unsupported push delivery, durable task scheduling, background worker queue, auto-execution, or polling should be claimed.
- Preserve bilingual English + Bahasa Indonesia localization, accessibility (`aria-live`, keyboard access, reduced-motion), and responsive hospital-white/sky-blue design.

## Nonnegotiable architecture invariants

Original Python backend contracts and strict critics stay untouched. Source lookup is read-only. Nemotron is triggered solely from explicit separate CaseLens/NextStep button clicks with a matching `evidence_snapshot_sha256` digest. Browser receives no SQL or API secrets. Proposed NextStep actions are never executed. `not_found` never means missed medical care. Audit records and local review notes are distinct histories; demo fixture mode has no fabricated Meterless events. Do not deploy the localhost proxy publicly.

## Deliverable

Improve the existing components and validate the 3 golden scenarios (`CASE-TB-001`, `009`, `018`), the accepted/rejected independent-agent paths, tab notifications, and the gated human review note. Run TypeScript/build checks and fix issues where dependencies are available. Preserve all working behaviors.
