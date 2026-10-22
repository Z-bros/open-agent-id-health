# E02 — Generate an evidence bundle from TBCARE_OS (post-kickoff)

This deterministic, **nonclinical** investigator reads the five fabricated
administrative source tables through the official Zetaris query helper.

All E01 retrievals were confirmed by the participant on 22 Oct 2026:
CASE-TB-001 had 5/5 table statuses available with matching fabricated source
identifiers. The runtime used namespace TBCARE_OS, not TB_CAREOS.

Run from your existing TB-CareOS checkout on feat/tb-zetaris-readonly-probe:

    git pull --ff-only
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.careflow.tb_reconcile \
      --namespace TBCARE_OS \
      --case-id CASE-TB-001 \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py

Then try CASE-TB-009 (lab documentation not returned), and CASE-TB-018
(result subject ID contradiction). These are *entirely synthetic* cases.

The command prints contract-shaped JSON (schema_version 1.0.0):
- observations: business event IDs, ingestion-row source provenance, source,
  subject reference, administrative timestamps, link metadata
- exceptions: cited ID/association mismatches, duplicate imported IDs, and
  unverified documentation gaps when a synthetic due date has elapsed
- source_checks: real current-query available / not_found / denied /
  temporarily_unavailable / error (attempt 1, not simulated access)
- requires_human_approval: always true

**Not yet implemented / do not overclaim:**
- source_checks.csv replay, visible_from_attempt filtering, two-attempt
  simulated source-recovery behavior, or source snapshot completeness proof
- synthetic chronology conflict categorization or precision/recall scoring
- Meterless World Model audit persistence; LLM explanations or NextStep planner
- proof of clinical relevance or missing care (none is justified by this data)

Never ingest source_checks.csv as a patient documentation table, never ingest
ground_truth_holdout.csv at all, and never send real medical data.

See shared/contracts/evidence_bundle.v1.schema.json.
