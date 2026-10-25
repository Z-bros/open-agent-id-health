# E09 — Cross-case integrity evaluation, fabricated TB metadata only

**Status:** Post-kickoff E09 evaluator created after participant browser
verification of Product Phases A, B, C (23 Oct 2026).

The evaluator measures **contract integrity and process safety**, not
medical performance or whether CareFlow has identified every true synthetic
exception. It uses actual read-only Zetaris retrieval for selected case
IDs and a deterministic offline NextStep critic. It deliberately does
**not** call NVIDIA, ingest a Meterless event, run proposed follow-up
queries, mutate any data, or read held-out ground truth.

## Run the live 36 synthetic-case evaluation in WSL2

Switch to the E09 branch from the repository root, first preserving
locally edited files through targeted Git stash if necessary:

    git fetch origin
    git switch --track origin/feat/e09-cross-case-evaluation
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Evaluate exactly the three demo cases first:

    PYTHONPATH=src:. python3 -m apps.evaluation \
      --case-ids CASE-TB-001 CASE-TB-009 CASE-TB-018 \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --output outputs/e09_golden_case_integrity.json

Then evaluate all 36:

    PYTHONPATH=src:. python3 -m apps.evaluation \
      --all \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --output outputs/e09_36_case_integrity.json

The script prints a brief summary and writes a detailed ignored local
JSON file with file mode 0600. A nonzero exit (2) means at least one
case failed validation, lacked any source evidence, or had impaired source
access. **Inspect the case_results array**; don't hide or discard failures.

The runbook does not claim the all-case evaluation passed until the
participant executes it and shares its results.

## Evaluation checks

- Only selected fabricated CASE-TB-001–036 case IDs, once per requested
  case. Exactly five first-pass source checks per returned live case.
- Business-ID citations of CareFlow findings must be present in the
  retrieved source observations.
- All cases preserve explicit human approval requirements.
- Offline deterministic NextStep plans must satisfy the actual critic,
  bounded source allowlist, final manual_review and stop.
- No actual plan queries are executed, no provider calls, and no
  held-out labels are read or passed to agents.
- Source errors are counted as **source_access_impaired**, not missing
  documents or clean cases. A case with zero observations is blocked.
- Invalid/mismatched evidence is counted as **failed_validation_or_read**,
  preserving the case ID and only a safe exception *type*.
- Status "not_found" records a successful empty **query**. It is never a
  clinical absence-of-care claim and doesn't verify snapshot completeness.

## Reporting caveat (important for hackathon judges)

The output does NOT measure:
- precision, recall, false negatives, or classification accuracy;
- Nemotron answer fidelity across 36 cases;
- verified patient care, clinical diagnoses or intervention outcomes;
- deployment security, reviewer identity or official registry state.

A separate offline, post-hoc labelled oracle evaluation can be planned
after inspecting the held-out dataset schema. The holdout must never be
read by the agents or the live product, and no label-derived metric
should be invented without an actual independent comparison.

## Synthetic fixture CI versus real live outcomes

The E09 unit suite mirrors a tiny CASE-TB-018 fabricated fixture to
36 IDs to stress the reporting/accounting logic **only**. The 36 mirrored
unit test cases are **not** 36 independent ground-truth examples. The
standalone E04 fixture has only three source checks, so the strict
five-table E09 evaluator correctly treats it as incomplete evidence for
an all-table evaluation. Real performance claims require running the
command against registered local Zetaris TBCARE_OS tables.
