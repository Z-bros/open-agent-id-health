# TB-CareFlow — Indonesian TB Follow-up Exception Agent

**Project direction locked 19 October 2026.** This is still a **pre-hackathon scaffold**; substantive build starts after 22 October 2026 00:00 UTC.

## Problem / user

For **Puskesmas TB programme coordinators**, follow-up evidence can be incomplete or inconsistent between screening records, diagnostic requests/results, and documented next steps. An investigator agent can reconcile *synthetic* records, highlight missing or conflicting handoffs, explain what evidence is absent, and prepare a staff-review worklist.

- WHO's July 2025 Indonesia TB epidemiological review documented inconsistent data submissions from puskesmas, reporting gaps, and incomplete digital integration.
- WHO's January 2026 programme review recommended faster referrals, fewer diagnostic delays and reduced loss to follow-up.
- **Important:** Kemenkes connected SSI Cek Kesehatan Gratis and SITB in April 2026. We are NOT proposing to rebuild that integration or its existing follow-up warnings. We are prototyping an explainable *exception investigation and resolution* layer; its incremental value still needs testing.

See [decision and evidence](docs/problem-decision.md) and [sources](docs/source-evidence.md).

## MVP (proposed)
1. Retrieve synthetic CKG screening / SITB pathway / lab result / staff follow-up records.
2. Match case and event identifiers, dates and expected documentation; distinguish true absence from unavailable sources.
3. Use a bounded investigate–critique–requery loop for anomalous cases (Zetaris + Meterless planned).
4. Output **evidence-linked exceptions for coordinator review**, not patient advice, outreach or clinical decisions.
5. Measure correctly identified exceptions, false alarms, traceable sources and simulated time.

**Not in scope:** disease diagnosis, treatment prescribing, medication adherence scoring, autonomous contact with patients, or a replacement for SITB/SATUSEHAT.

## Quick start (pre-existing deterministic prototype)
```bash
python -m pip install -e .
healthagent --list
healthagent --case CASE-TB-CONFLICT
python -m unittest discover -s tests -v
```
Current fixtures also include generic referral and diagnostic cases left over from the pre-hackathon scaffold. These will be replaced with TB-only fixtures in the official build window.

## Repository
- `src/healthagent/`: typed models, generic deterministic investigation workflow, CLI, sponsor stubs
- `data/synthetic/`: entirely fabricated cases
- `tests/`: five offline regression tests
- `docs/`: problem evidence, architecture, sponsor plan, demo, submission
- `.github/workflows/`: automated tests

**Current implementation status:** deterministic foundation only. No live Zetaris, Meterless, medical system, LLM, or patient data integration yet.

## Competition
22–27 October 2026 UTC; submission deadline **27 Oct 23:45 UTC = 28 Oct 06:45 WIB**. Required sponsor integrations: Zetaris and Meterless; development in Cursor with Space XAI. Track to be confirmed; Track 01 (fragmented intelligence) is a strong candidate.

## Ethical and operational safety
All data in this repository must be synthetic or properly licensed and de-identified. Findings mean a **review is needed**, never automatic proof of missed care. Human authorization is required for patient communication, clinical decisions, and changes to official records. No credentials in git.

**Pre-existing work disclosure:** Generic scaffold generated **19 October 2026**, before official build begins 22 October. Declare it explicitly in the HackOS submission.
