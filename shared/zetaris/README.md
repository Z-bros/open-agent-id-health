# Zetaris read-only probe — post-kickoff E01/E02 implementation

**Status (22 October 2026 WIB):** New TB-v1-aware read-only source probe with
offline tests. CI has passed. **Not yet demonstrated** against participant's
actual Zetaris runtime or registered TB tables. E01 GO requires a real SQL
query returning fabricated evidence and source IDs.

## Verified original prebuild ZIP

The separately prepared 36-case synthetic ZIP has now been supplied and its
bundled verifier passed (36 cases, 163 evidence rows, 216 synthetic source checks,
and 36 held-out labels). The ZIP, including 21 Oct generation, is pre-existing.

- Five evidence tables: cases, screening_events, lab_orders, lab_results,
  followup_events. These are the ONLY tables the evidence probe queries.
- source_checks.csv: replay-harness metadata; NOT clinical documentation.
  Original handoff's six source files = five evidence tables plus simulation.
- ground_truth_holdout.csv: scoring only; NEVER give to agent/Zetaris.
- The entire extracted data/synthetic/tb_v1/ is gitignored.
- All five tables have case_id. Event row provenance is ingest_row_id except
  cases (case_id); business IDs differ by table (event_id, order_id,
  result_id, followup_event_id). Duplicate business IDs may be intentional.
- visible_from_attempt and simulated source access must be applied in the
  later retry harness. This raw data-access probe DOES NOT apply them.

## Implemented

- shared/zetaris/readonly.py: bounded allowlisted SELECT, verified Python
  helper path, no invented HTTP route, no arbitrary table access/writes.
- apps/careflow/tb_zetaris_probe.py: summarizes five evidence table queries
  with source provenance, business IDs and explicit error categories.
- This is NOT YET contract-valid evidence_bundle.v1 reconciliation or a
  demonstration of actual sponsor integration.

## WSL2 instructions

From the local TB-CareOS repo feature branch:

    git pull --ff-only
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Download the original full ZIP to your computer. Its internal directory is
tb_v1/. Extract from TB-CareOS root (replace the local ZIP path):

    mkdir -p data/synthetic
    python3 -m zipfile -e "/path/to/tb-careflow-synthetic-v1.zip" data/synthetic
    python3 data/synthetic/tb_v1/verify_dataset.py

**Zetaris import:** load ONLY the five evidence CSVs. Do not ingest the
source_checks simulation or ground_truth_holdout. Files on WSL2 cannot be
assumed accessible by Zetaris: official getting-started documentation uses
CREATE LIGHTNING FILESTORE TABLE on accessible object storage. Confirm the
installed local Zetaris edition's CSV upload/registration workflow, storage
location, team namespace and write permission BEFORE creating any objects.
See https://github.com/zetaris/getting-started/blob/main/open_data/parquet_csv/HOWTO.md

When the tables exist in your assigned namespace and use the same names as
the CSV stems, inspect the generated SQL without contacting Zetaris:

    python3 -m apps.careflow.tb_zetaris_probe \
      --namespace YOUR_AUTHORIZED_NAMESPACE --case-id CASE-TB-001 --dry-run

The official query_zetaris.py script loads its own ignored .env.local and
calls the documented UI proxy. Verify its own SELECT 1 smoke test:

    python3 /path/to/zetaris-getting-started/scripts/query_zetaris.py "SELECT 1"

Execute the five-source read-only probe only after table registration:

    python3 -m apps.careflow.tb_zetaris_probe \
      --namespace YOUR_AUTHORIZED_NAMESPACE \
      --case-id CASE-TB-001 \
      --helper /path/to/zetaris-getting-started/scripts/query_zetaris.py

Suggested fabricated demo cases: CASE-TB-001 (complete), CASE-TB-009
(no result document row), CASE-TB-018 (mismatched synthetic subject ref).
An empty raw query is NOT proof of missed care. Keep all clinical decisions
with qualified human staff.

If Zetaris returns an unfamiliar JSON shape, capture its **redacted**
response shape locally; update the parser only after inspecting evidence.

## Next acceptance gate

A real Zetaris query must return fabricated records with provenance IDs.
No local code/CI success alone proves E01 integration. Continue next with
CareFlow evidence_bundle.v1, simulated source retries/visibility, Meterless
events and coordinator dashboard.
