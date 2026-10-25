# TB-CareOS product MVP — required after backend integration

**Current status (22 Oct 2026):** E01–E06 are demonstrated for the one fabricated
case CASE-TB-018. E08 Meterless audit of CaseLens and NextStep is being tested.
The current E06 HTML report is useful for verification but **NOT** the
interactive product. Do not describe it as a finished application.

## Required product experience

The target user is a fictional Puskesmas administrative TB coordinator
reviewing **only synthetic case evidence**. The MVP must demonstrate a
complete, clickable, safe workflow:

1. **Case explorer:** list/search the available fabricated case IDs, show
   source coverage, and clearly flag exceptions, without real identities.
2. **Case detail:** show evidence timeline, source status and exact synthetic
   provenance/business record IDs. A missing query result is not missed care.
3. **Run investigation:** the UI initiates bounded CareFlow reconciliation
   and, when selected, Nemotron CaseLens explanation and NextStep planning.
   Provider errors fail visibly; no mocked result silently replaces a failure.
4. **Human-review queue:** show reason, citations and proposed checks; allow
   a user to record a locally auditable **administrative review disposition**.
   No automated approval, patient contact, clinical recommendation, or
   writes to Zetaris/official health systems.
5. **Audit:** show source evidence and versioned agent report events from
   Meterless, and locally recorded human decisions with explicit provenance.
   Distinguish source event time from AI run time and review time.
6. **Demo modes:** at least the three golden cases CASE-TB-001 (no
   exception), CASE-TB-009 (lab document not returned by query) and
   CASE-TB-018 (subject mismatch). The held-out labels are NEVER agent input.

## Practical implementation

Preferred provisional stack:
- **Python API (FastAPI):** thin layer over existing tested Zetaris
  retrieval, CareFlow, CaseLens, NextStep and Meterless adapters. Secret
  credentials remain server-side; expose only allowlisted fabricated cases.
- **Next.js + Tailwind CSS:** responsive case queue, case details, source
  comparisons, explain/plan panels, review workflow and audit timeline.
- **Local demo:** run API and frontend through WSL2 for deterministic,
  reproducible judging. External deployment is optional, not a prerequisite.
- **Persistence:** Meterless for agent/source audit, plus an explicitly
  scoped local-only human-review decision log. Never alter synthetic
  administrative source evidence as a side effect of a review decision.

Draft backend API boundaries, to implement rather than claim are working:
- GET /api/cases — bounded fabricated case list
- GET /api/cases/{case_id}/evidence — read-only evidence bundle
- POST /api/cases/{case_id}/explain — bounded Nemotron explanation, error surfaced
- POST /api/cases/{case_id}/plan — safe verification plan only, no execution
- GET /api/cases/{case_id}/audit — previously persisted synthetic audit
- POST /api/cases/{case_id}/reviews — explicitly authorized local reviewer note
  only; not an official system update

## Product acceptance criteria

- A first-time judge can open the app and complete the synthetic
  CASE-TB-018 evidence-to-human-review journey without terminal commands.
- Full links from findings to exact retrieved source IDs and timestamps.
- Agent invocation visibly differentiates loading, complete, failed and
  awaiting-human-review states.
- Proposed source checks have no "execute" or outreach side effect.
- A review choice is never treated as a diagnosis or official-system action.
- Case explorer, CaseLens, NextStep and audit are genuinely wired to the
  working Python backend rather than hard-coded UI mock data.
- A three-case recorded walkthrough and fresh-install reproducibility checks.
- Keyboard usability, responsive layout and no credential exposure.
- If a part is unimplemented, label it unimplemented in the demo.

## Ordered remaining work — product is not optional polish

1. Finish the bounded Meterless E08 event audit (backend).
2. **Product phase A:** implement thin Python API and clickable case explorer.
3. **Product phase B:** wire CaseLens/NextStep and review queue to that API.
4. **Product phase C:** connect audit view and improve demo ergonomics.
5. Evaluate multiple synthetic cases, failure modes, injection resistance,
   model citations, and reproducible setup.
6. Record demo, produce screenshots and submit before
   28 Oct 2026 at 06:45 WIB (from the orientation).

An attractive static HTML file is not sufficient to claim product completion.
