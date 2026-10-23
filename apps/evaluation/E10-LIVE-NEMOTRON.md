# E10 — Live Nemotron acceptance evaluation

E09 passed 36/36 synthetic administrative integrity checks but used zero model calls.
E10 makes real hosted NVIDIA Nemotron 3.5 Lightning requests through the
existing CaseLens and NextStep validators, with no data writes, oracle
access, patient outreach or proposed source-query execution.

**Metric:** accepted JSON/grounding/bounded-action contracts, not measured
medical accuracy, recall, clinical outcomes or guaranteed hallucination-free
explanations. Never equate passing the critic with absolute factuality.

## Default representative sample

One case per administrative category, plus a no-finding case:

- CASE-TB-001: no rule-based finding, zero model calls expected
- CASE-TB-002: duplicate event replay
- CASE-TB-004: follow-up document not returned in query
- CASE-TB-007: cross-source link mismatch
- CASE-TB-009: lab document not returned in query
- CASE-TB-018: synthetic subject mismatch

At most 10 actual model calls for this six-case default. Repeats=2
may make 20 calls on the **same frozen source snapshot**. No silent
offline fallback is allowed after a provider error or failed validator.

## Ubuntu WSL2 commands

Fetch the E10 branch, safely preserving any conflicting local edits:

    git fetch origin
    git switch --track origin/feat/e10-nemotron-live-reliability
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Ensure the NVIDIA key is in this exact WSL shell; never echo its value:

    python3 -c 'import os; print(bool(os.getenv("NVIDIA_API_KEY")))'

If the value is False, set it privately:

    read -rsp "NVIDIA API key: " NVIDIA_API_KEY
    echo
    export NVIDIA_API_KEY

One case first, at most 2 hosted calls:

    PYTHONPATH=src:. python3 -m apps.evaluation.nemotron_reliability \
      --case-ids CASE-TB-018 \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --output outputs/e10_case018_live.json

Then the six-category representative test, at most 10 calls:

    PYTHONPATH=src:. python3 -m apps.evaluation.nemotron_reliability \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --output outputs/e10_representative_live.json

Optional second run on the same source snapshot, up to 20 calls:

    PYTHONPATH=src:. python3 -m apps.evaluation.nemotron_reliability \
      --repeats 2 \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --output outputs/e10_repeated_live.json

A nonzero exit indicates any rejected/failed model output or source
evaluation failure; the bounded JSON report is saved even on failure.

## Meaning of counts

- model_calls: actual provider complete() invocations
- provider_accepted: successful real replies accepted by deterministic
  output, citation and bounded-planning validators
- rejected_or_failed: provider/network/timeout or critic failure, with
  safe error category only (no raw model text or credentials)
- no_provider_needed: no findings or no permitted NextStep lookups; such
  cases are excluded from the model acceptance denominator
- cases_without_verified_sources: cannot safely evaluate that evidence
- proposed_queries_executed: always zero; only proposals are produced

The CLI never loads ground_truth_holdout.csv. Even 100% accepted calls
do not prove 100% explanation factual accuracy, independent clinical
validity or performance on all 36 cases.

## After this test

Freeze the demo for CASE-TB-001, 009 and 018, prepare screenshots and
partner integration proof, architecture, model evaluation, safety disclosure,
quickstart, and final hackathon submission before 28 Oct 2026 06:45 WIB.
