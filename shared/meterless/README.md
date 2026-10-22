# E03 — Meterless World Model audit integration

**Status:** New E03 integration code built 22 October 2026 WIB. Upstream
reference is external and pinned for CI. A passing upstream reference test
does not itself prove that the participant's LOCAL Zetaris-to-Meterless path
has been exercised. Report it separately after local end-to-end verification.

## What the bridge does

1. Fetch real fabricated records with CareFlow via the Zetaris UI proxy
   query helper (the participant already verified E01 and three E02 cases
   in namespace TBCARE_OS).
2. Emit versioned evidence_bundle.v1. No oracle labels or real patient data.
3. Map each source record to a stable Meterless IngestObservation:
   - externalId = case + record_type + exact ingestion source_record_id
   - original record IDs, subject refs, link metadata and source times
     remain present in the observation text and source provenance
   - case ID is a shared semantic entity for cross-source clustering
4. Produce a distinct derived investigation snapshot with the current
   source statuses, findings and explicit timestamp_basis metadata.
   The summary's "at" is anchored to the latest synthetic evidence time,
   NOT to the wall-clock time of the SQL query.
5. Run the **real** WorldModel.ingest in the external Meterless TypeScript
   reference in local persistent storage, replay the same batch, then
   reload a fresh WorldModel instance from disk and compare projections.
6. Return an evidence trace with event count and timeline sample.

The re-ingest invariant is **no new source events and identical projection**;
the World Model's own operation/audit log may legitimately record an
additional ingestion attempt. Do not claim the audit log is byte-identical.

## Setup (WSL2 / Cursor)

The project code expects your separate Meterless checkout. Use the path
for your existing checkout if you already installed it.

    cd ~
    git clone https://github.com/Meterless/Meterless.git Meterless

To match the pinned version tested in CI:

    cd ~/Meterless
    git checkout 1742dec56a66e58eef9dda2d2b865823758ca8cd
    cd engines/world-model/reference
    npm ci
    npm test
    npx tsx scripts/idempotency-check.ts

Do not change anything in the upstream repo; we import its TypeScript source
at runtime. The Python/TS boundary is a local, bounded JSON-over-stdin
subprocess, and the state is stored in gitignored local_data/meterless/.

## First end-to-end test

From the TB-CareOS feature branch (do not merge a draft until review):

    cd /path/to/open-agent-id-health
    git pull --ff-only
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --namespace TBCARE_OS \
      --case-id CASE-TB-001 \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --reference ~/Meterless/engines/world-model/reference

Run that same command AGAIN. After successful first ingestion, the next
run should show first_run.processed=0 and replay.events_appended=0, while
persisted_projection_matches=true. The bridge also re-ingests internally on
each run and checks its projection/append invariants.

Then test synthetic discrepancies separately:

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-009 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --reference ~/Meterless/engines/world-model/reference

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --reference ~/Meterless/engines/world-model/reference

Cases are isolated by stable Meterless namespace and persistent file. Saved
bundles can also be tested via --bundle-file (without querying Zetaris).
The per-case report shows actual event counts and timeline samples.

## Scope and constraints

- The World Model reference is a local TypeScript implementation, NOT an
  assumed Meterless hosted LLM inference API.
- No inference model, medical workflow automation, patient contact, or
  real patient evidence is involved.
- Query failures remain explicitly tagged; no missing row proves absent
  clinical care.
- The v1 evidence contract has no query performed-at timestamp, so current
  query runs are stored as derived snapshots anchored to evidence time;
  audit timestamps must not be used to reconstruct exact query times.
- Investigation summary updates use new stable content-derived IDs; prior
  summaries stay in the append-only event log.
- Production durability, concurrency hardening and auth are not proven by
  the upstream reference; JSON-file persistence is suitable for a small
  synthetic hackathon demo only.
- Meterless and Zetaris starter work were previously checked before 22 Oct;
  this application-specific bridge and new E03 smoke workflow were added
  during the build window.

CI: .github/workflows/meterless-integration.yml tests a pinned public upstream
commit with a small post-kickoff synthetic bundle, repeating the operation
across two processes. It is separate from participant-local live Zetaris
integration and should be described as such.
