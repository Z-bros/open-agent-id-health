# Project decision — TB-CareFlow

**Decision:** SELECTED, 19 October 2026. No further broad problem ideation unless critical feasibility or safety blocker appears.

## One-sentence problem
**Puskesmas TB programme coordinators** need to identify *unresolved administrative handoffs* across TB screening, testing, and follow-up records, particularly when a result is missing, inconsistent, delayed in source systems, or not yet documented as acted upon.

This is a proposed narrow workflow problem grounded in reported surveillance/data-quality gaps. **We have not measured a national rate of missed follow-ups**, and should not claim one.

## Supporting sources
1. WHO Indonesia, 1 July 2025: TB epidemiological review reported inconsistent data submissions from puskesmas, private-sector reporting gaps and limited digital integration. https://www.who.int/indonesia/news-room/item/01-07-2025-strengthening-tb-surveillance-to-accelerate-indonesia-s-path-to-elimination
2. WHO Indonesia, 8 January 2026: national programme review recommended faster referral, reduced diagnosis delay and loss to follow-up. https://www.who.int/indonesia/news/detail/08-01-2026-indonesia-charts-next-phase-of-tb-response-through-national-programme-review
3. Kemenkes, 25 March 2025: 889,000 TB notifications (2024), 81% reported achievement in drug-susceptible TB treatment initiation vs 90% target. https://www.kemkes.go.id/id/47510/Pada-2025-target-nasional
4. Kemenkes, 15 June 2026: SSI CKG and SITB data integration in place since April 2026; existing follow-up warnings and early screening-risk classification. https://setjen.kemkes.go.id/news/kemenkes-ri-perkuat-eliminasi-tb-melalui-integrasi-data-satusehat-indonesiaku-dan-sitb

## Existing systems and differentiation
SITB + SSI CKG / SATUSEHAT are **existing national government systems**. TB-CareFlow **does not replace or claim to newly bridge** these systems. Our unvalidated product hypothesis is that explainable cross-record *exception investigation* and audit-ready coordinator handoff could complement the existing data flows.

## MVP user story
As a Puskesmas TB programme coordinator, I submit or select a synthetic case; the agent looks for screening/diagnostic/follow-up records, investigates missing/contradictory evidence with bounded queries and produces a source-linked worklist of items needing confirmation.

## Three golden scenarios
1. Screening → diagnostic result → documented action all present: no unsupported alarm.
2. Screening/diagnostic request present; result missing after retries: label **unavailable evidence**, request human verification (never infer missed examination).
3. Lab result and SITB event refer to different synthetic identifiers or conflicting timestamps: detect discrepancy and show source references for staff reconciliation.
Stretch: retrieval temporarily unavailable then recovers on retry; duplicate records.

## Evaluation and finish line
- Exception precision/recall on *synthetic, labelled scenarios*
- Unsupported assertion rate (goal zero for test cases)
- Source attribution completeness
- Successful recovery under transient failures
- Deterministic baseline vs sponsor-backed agent comparison

## Scope and safety
Synthetic data only. No autonomous diagnosis, prescription, referral routing, patient contact, or edits to official records. Require coordinator approval.

## Planning closure
- [x] Exactly one use case and user
- [x] National scale and process-specific published evidence
- [x] Existing Indonesian solutions identified
- [x] Three golden scenarios and agent output defined
- [ ] Sponsor accounts and integration interfaces verified
- [ ] Expanded TB-specific dataset generated
- [ ] End-to-end sponsor-backed loop tested (build window)

**Track candidate:** Track 01 — Solving Fragmented Intelligence; confirm on HackOS.
