# TBCare hackathon submission readiness — 25 October 2026

This is a **verification ledger**, not an assertion of clinical or production readiness. Only fabricated TB-program administrative data may appear in the demo.

| Area | Established evidence | Remaining acceptance |
| --- | --- | --- |
| Live read-only Zetaris | E09: 36/36 query-readable synthetic cases, 163 observations, 21 rule findings | No official SITB/SATUSEHAT integration; source completeness is not implied |
| CareFlow | Deterministic source-cited discrepancies and query-access categories | Held-out oracle-based precision/recall not measured |
| CaseLens | Real hosted inference through Python and strict validator; selected six-case E10 accepted 3/5 CaseLens calls | Rejection and provider failures must remain visible |
| NextStep | Bounded allowlisted proposed checks and independent Python critic; E10 selected 5/5 valid plans | No proposal is executed |
| Browser bridge | 25 Oct CASE-TB-006 actual evidence + observed model activity in local Next.js mode | Full clean-clone/browser accessibility signoff |
| Meterless | CASE-TB-006 manual source + saved validated CaseLens/NextStep report archival, 18 canonical events; replay yielded zero new canonical events | No automatic UI archival or run-ID correlation |
| Human review | Local notes with SHA256 snapshot guard, idempotency and fictional label | Reviewer identity not verified, not a real administrative approval |
| Frontend source | Optional Next.js v0.3.1 included in `main` via PR #23 | Both frontend source/typecheck/demo-build workflows passed at final integration head `9572ef8`; local WSL clean-clone/browser acceptance remains; no tracked lockfile, so use `npm install` rather than `npm ci` |
| Publication | PR #23 **merged into `main` on 25 Oct 2026** (`325b27e`); repository is public | Review existing Git history/branches/Actions for secrets and complete independent local acceptance; merge alone is not a security audit |
| Submission | Architecture, demo cases, evaluation disclosures and runbooks | Record a 1–4 minute video; attach a slide deck, repository, sponsor-tech explanation, pre-existing work disclosure, and team/track fields; submit via HackOS before deadline |

## Suggested judge walkthrough (synthetic only)

1. Start the Python API with the local Zetaris helper, NVIDIA key and Meterless reference; start Next.js in `local` mode.
2. Open `CASE-TB-001` and point out that zero emitted findings **does not prove complete healthcare delivery**.
3. Open `CASE-TB-009`; a query returning no lab-result row is an **unverified documentation gap**, not evidence of missed care.
4. Open `CASE-TB-018`; compare `CASE-TB-018` and `RES-TB-018` synthetic subject references; explicitly invoke CaseLens and NextStep, confirm returned citations, no executed plans, human-review requirement.
5. Optionally show `CASE-TB-006` as independently observed agent execution, and the historical Meterless World Model events that were archived through the **separate manual CLI**. The activity log and audit log are **different systems**.
6. Show one rejected/incomplete inference as a clear fail-closed outcome rather than an invented success.

## Submission claims to avoid

No patient diagnosis, treatment outcome, real hospital interoperability, official SATUSEHAT/SITB endorsement, guaranteed source completeness, clinical accuracy, stable model acceptance rates beyond tested sample, automated patient contact or verification, automatic case clearance, authenticated staff approval, automatic Meterless agent archival or unified per-run decision trace.

Original verified reports: [E09](../e09-verified-evaluation-results.md) and [E10](../e10-verified-nemotron-results.md). World Model integration: [E03](../e03-meterless-runbook.md) and [E08](../../shared/meterless/E08-AUDIT.md).

**Deadline from hackathon orientation:** 28 October 2026, 06:45 WIB. Target submit 27 October.

## CI baseline and release boundary

The final PR head `9572ef8664e8dd2a0e27e077b42cbb0594c07d62` passed all four GitHub Actions workflows (offline Python, upstream Meterless, two optional frontend builds) before **PR #23 merged into `main` at `325b27e7b909e65b71d18cd77e2c9e992c620936`** on 25 October 2026. These workflow results validate source and fixture behavior, **not** fresh WSL clean-clone/live Zetaris, model credential reliability, or browser accessibility. GitHub merge confirmation is not a HackOS submission.

For the actual organizer-required submission fields and a four-slide storyline see [`HACKOS-PACKAGE-2026-10-25.md`](HACKOS-PACKAGE-2026-10-25.md). Track 01 is the current recommendation, **not an already confirmed HackOS selection**.
