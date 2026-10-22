# E03 — Real Meterless World Model integration (22 Oct 2026)

## What has actually been verified

E01: user performed a live authenticated Python -> Zetaris query against the
five fabricated source tables under **TBCARE_OS**, including their source IDs.

E02: user ran real Zetaris-backed CareFlow reconciliation for three golden cases:
- CASE-TB-001: 5 observations, no exceptions.
- CASE-TB-009: lab-result document not returned; no missed-care assertion.
- CASE-TB-018: subject mismatch; cites CASE-TB-018 and RES-TB-018.

E03 (this branch): Python converts the existing evidence_bundle.v1 into stable,
source-linked Meterless IngestObservation inputs. The TypeScript sidecar loads
the **actual upstream Meterless World Model reference** and calls
WorldModel.ingest(), persists under outputs/meterless/.world/, and checks
replay idempotency. The GitHub Actions job tests genuine upstream integration
using only a locally saved **synthetic** E02 fixture, including persisted
storage reload. This does NOT prove that the local user installation has been
run successfully with actual live Zetaris records.

## Reuse an existing Meterless checkout if possible

Look for the existing reference path in WSL2:

    find "$HOME" -maxdepth 7 -path '*/engines/world-model/reference/package.json' -print 2>/dev/null

If found, set:

    REFERENCE=/ACTUAL/PATH/engines/world-model/reference

Otherwise download Meterless itself (do not copy vendored source code into
TB-CareOS):

    git clone --depth 1 https://github.com/Meterless/Meterless.git ~/Meterless
    REFERENCE="$HOME/Meterless/engines/world-model/reference"

Inspect the upstream repository and confirm node/npm:

    node --version
    npm --version
    cd "$REFERENCE"
    npm ci
    npm test
    npx --no-install tsx scripts/idempotency-check.ts

The reference implementation has Apache-2.0 licensing. This project uses it
as an external checkout (not repackaged inside TB-CareOS).

## Run E03 against the actual live synthetic Zetaris case

From your TB-CareOS repository root (use existing worktree/branch):

    git fetch origin
    git switch --track origin/feat/meterless-world-model-integration
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-018 --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --reference "$REFERENCE" \
      --state-dir outputs/meterless

This asks the existing E02 reconciler to use **real Zetaris SQL** read-only.
World Model receives only the resulting synthetic administrative evidence,
safely under a per-case namespace. The helper's auth is kept in its own
ignored local .env.local and never copied to a World Model event.

The output summarizes:
- first pass: number of new source observations/finding events added
- second same-batch pass: processed=0, events_appended=0, state_unchanged=true
- durable state: persisted event count and audit entry count, recent event IDs

Run exactly the same command **again** to prove idempotency across restart:
its first pass should process 0 new observations, with no new canonical events.
The World Model may still append separate **audit log entries** about the replay
attempt itself; this is expected and not evidence duplication.

### Important: derived projection rehydration on restart

Verified by participant on 22 Oct 2026: after restarting the E03 command for
CASE-TB-018, first pass processed=0, events_appended=0, observation_count=6,
durable event_count=18, and the immediate replay was unchanged, while
first_pass.state_changed=true. The audit count increased from 14 to 16.

This is consistent with the **upstream Meterless reference** persisting its
event log, observations and stories but rebuilding some entity aggregate
fields during subsequent ingest. The store's event fold does not persist the
post-ingest derived `entity.aggregates` projection directly; on reopening,
re-ingestion of an unchanged batch may repopulate derived state. This is **not**
a new evidence event. Our sidecar now explicitly flags this as
`first_pass.derived_projection_rebuilt_on_reload=true` rather than treating
it as proof that new source evidence was added.

E03 event-store replay idempotency passed. Strict no-op canonical-state
rehydration on cold startup **has not** been proven; address through upstream
projection regeneration on load or a separately verified materialized snapshot
before claiming byte-for-byte cold-start canonical state equivalence.

For an offline fixture-only check (no Zetaris call):

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-018 \
      --bundle tests/fixtures/tb_case_018_bundle.json \
      --reference "$REFERENCE" \
      --state-dir outputs/meterless-fixture

The complete pre-existing 36-case ZIP and its ground-truth holdout are NOT
passed to Meterless; all work here is synthetic and administrative.

## Implementation and safety limitations

- This is a **deterministic evidence ingestion** layer using Meterless World
  Model. It is not an LLM/ Nemotron inference endpoint.
- Observations are event-sourced, identified by stable source row IDs.
  Findings have stable keys based on category + cited business record IDs;
  edited findings can supersede earlier facts without erasing audit events.
- Replay tests check canonical state and event counts. The audit has an
  append-only record of both ingestion attempts.
- There is no clinical action, patient outreach, or connection to actual
  SITB/SATUSEHAT data.
- Source simulation (source_checks.csv, visible_from_attempt), chronology
  interpretation, broader benchmark metrics, and human-review dashboard
  remain separate future milestones.
