# TBCare — HackOS final submission package (as of 25 Oct 2026)

> This is a **working submission checklist**, not a submitted entry, a completed clean-clone acceptance, or clinical product clearance. All examples use fabricated records. PR #23 was merged into `main` with explicit approval on 25 October 2026; this does not complete HackOS submission or participant-side runtime acceptance.

## Entry positioning

- **Product:** TBCare — synthetic tuberculosis administrative **evidence reconciliation**, not diagnosis or medical decisions.
- **Primary track recommendation:** Track 01, *Solving Fragmented Intelligence*. It fits the five-source Zetaris reconciliation and citations. The final HackOS track has **not been confirmed**; select exactly one track in the official form.
- **User:** a fictional Indonesian Puskesmas TB coordinator investigating whether a digital documentation discrepancy needs administrative human review.
- **Value:** identify cross-source discrepancies and provide cited reasons, bounded **proposed** verification steps, preserved audit evidence, and an explicit human-review checkpoint.
- **Do not claim:** real SITB/SATUSEHAT connectivity, authorized staff accounts, clinical decisions, automatic check execution, patient contact, case clearance, or automatic agent-result archival.

## Required submission inventory (orientation, p. 10)

| Requirement | What to provide | Status (25 Oct) |
| --- | --- | --- |
| 1–4 minute demo video | Record the *actual* application flow, not a mockup-only animation | **Not recorded/verified here** |
| Slide deck | Problem, user, solution, architecture; suggested four-slide script below | **Needs export and attachment** |
| GitHub repository | Public `Z-bros/open-agent-id-health`; integrated source and README are now in `main` following PR #23 | **Merged at `325b27e`; fresh participant-side acceptance still needed** |
| Sponsor explanation | Evidence of genuine Zetaris and Meterless, Cursor build environment and any actual NVIDIA usage | **Documentation available; final write-up needed** |
| Pre-existing components | Clearly disclose earlier generic prototype, pre-kickoff monorepo/schema, installation checks and prepared synthetic TB-v1 dataset | **Disclose explicitly** |
| Project details | Product name, team members, one selected track, description | **Finalize in HackOS** |

**Submission hard stop:** Tuesday **27 October 2026, 23:45 UTC = Wednesday 28 October 2026, 06:45 WIB**. Internal goal: 27 October, 21:00 WIB. Official times are from participant orientation (pages 5, 10 and 13); confirm the submission interface before submitting.

## Four-slide outline

1. **Problem & user** — fabricated Indonesian TB-program records are fragmented across screening, lab and follow-up tables. Missing query rows do **not** prove missing care.
2. **Workflow & outcome** — a coordinator opens CASE-TB-009/018, inspects actual retrieved source IDs, receives citation-grounded explanations and *unexecuted* verification proposals, then makes a local fictional review note.
3. **Architecture & reasoning** — Zetaris read-only SQL → CareFlow deterministic findings → on-demand CaseLens + NextStep hosted Nemotron with strict separate validation → human checkpoint. Meterless World Model is genuinely used for **separate CLI** archival/replay; read-only audit events and server-observed activity are distinct ledgers.
4. **Evidence, limits & impact** — E09 36/36 synthetic source/contract checks (163 observations, 21 deterministic findings); E10 8/10 agent output-contract acceptances across 10 actual requests; manual CASE-TB-006 archival yielded 18 events and no added duplicates on replay. No clinical accuracy, ground-truth precision/recall, automatic clinical decision or official-source coverage claim.

## Suggested 2–3 minute demonstration

1. **0:00–0:25** — synthetic-only disclaimer and the user problem; show `CASE-TB-001` as *no rule-based finding*, **not** evidence of complete care.
2. **0:25–0:55** — `CASE-TB-009` and its lab query returning no row; cite query status and source IDs.
3. **0:55–1:45** — `CASE-TB-018` subject-reference mismatch; user explicitly triggers CaseLens and NextStep; inspect independent validation/status, citations and human-review-required labels. If hosted inference fails, show the *actual* fail-closed error and continue; do **not** manufacture an accepted response.
4. **1:45–2:20** — local fictional review note; read-only Phase G activity and, if actual upstream state is loaded, historical Meterless audit. Clarify that browser actions **do not** automatically archive validated agent reports.
5. **2:20–2:45** — show GitHub repository, reproducibility commands, positive and negative checks, limitations, and hand off decision to the human.

## Sponsor integration wording (truthful)

- **Zetaris (required):** five read-only locally registered fabricated tables in `TBCARE_OS`, source IDs and retrieval statuses. Point to `shared/zetaris/readonly.py` and E09.
- **Meterless (required):** upstream World Model event ingestion, persisted history, idempotent replay, and separate read-only audit. Point to `shared/meterless/adapter.py`, `scripts/meterless-world-model.mts`, E03/E08, and the genuine upstream CI; do not call this an LLM.
- **Cursor (required dev environment):** describe the actual editing/testing used in Cursor and Space XAI only to the extent demonstrable; no fictional usage logs.
- **NVIDIA:** actual hosted Nemotron CaseLens/NextStep calls documented by E10, and real responses within participant's current demo. Do **not** imply the optional NVIDIA compute grant or GPU infrastructure was used unless verifiable.

## Final release gate checklist

- [ ] Review all public commit history, branches, Actions output and local config for secrets; public repository is **not** a security audit.
- [ ] Cold-clone default `main` in participant WSL and run Python unit suite; start Zetaris-backed Python app.
- [ ] Frontend: `cd apps/tbcare-next && npm install --no-audit --no-fund && npm run test:static && npm run test:agentic && npm run test:integration && npm run test:brief && npm run typecheck && npm run build`. No tracked npm lockfile currently; `npm ci` is inappropriate.
- [ ] In separate terminals start Python on 8765 and Next.js on 3001 with **localhost-only** opt-in proxy; verify sources and independently triggered model calls for 001, 009 and 018.
- [ ] Check responsive layout, keyboard navigation, error recovery, genuine and rejected model responses, human-review persistence, actual Meterless events.
- [x] PR #23 merged into `main` at `325b27e7b909e65b71d18cd77e2c9e992c620936` with explicit user approval. **Still pending:** participant clean-clone browser/runtime acceptance; CI does not substitute for it.
- [ ] Export final deck, record 1–4 min screen capture, confirm team/track and sponsor write-up, and submit on HackOS before the UTC deadline.

**Source of truth:** [root README](../../README.md), [submission readiness](tbcare-submission-readiness-2026-10-25.md), [quickstart](../SUBMISSION-QUICKSTART.md), [pre-existing disclosure](../prebuild-disclosure.md), [E09 evidence](../e09-verified-evaluation-results.md), [E10 evidence](../e10-verified-nemotron-results.md), and [the merged PR](https://github.com/Z-bros/open-agent-id-health/pull/23).
