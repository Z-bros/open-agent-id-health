# Zetaris adapter — post-kickoff read-only evidence probe

Status: **new code written during the official 22 Oct 2026 build window**. The
read-only adapter and 12 offline unit tests are implemented; this is **not**
yet verified against the participant's live local Zetaris platform or the
separate 36-case TB-v1 dataset.

## What is implemented

- The new readonly.py uses the documented Python query helper in the official
  Zetaris getting-started repository:
  https://github.com/zetaris/getting-started/blob/main/scripts/query_zetaris.py
  It **does not** invent an endpoint or copy credentials into TB-CareOS.
- A single SQL SELECT is allowed. Fabricated case IDs, namespace names,
  source names and row limits are validated. ground_truth_holdout is excluded.
- python3 -m apps.careflow.tb_zetaris_probe queries the six allowlisted
  synthetic evidence sources, summarizes result counts/source record IDs,
  and distinguishes a successful empty result (not_found) from outages,
  authorization failures and unrecognized result formats.
- No direct clinical action, real patient source, automated write, or data
  upload is performed by the probe.

## Read-only local instructions (participant's WSL2/Cursor machine)

1. Check out the official Zetaris getting-started repository **you already
   have**. The checked-out scripts/query_zetaris.py must work using its
   documented .env.local credentials; keep this file outside Git.
2. Confirm the **six actual TB-v1 CSV headers** and which namespace has the
   six registered fabricated source tables. The initial probe expects each
   source to have a case_id column; do not run it as-is if the actual CSV
   headers differ. Do not register ground_truth_holdout.csv.
3. Inspect generated SQL without contacting Zetaris:

       python3 -m apps.careflow.tb_zetaris_probe \
         --namespace YOUR_TEAM_NAMESPACE --case-id YOUR_SYNTHETIC_CASE_ID --dry-run

4. After registering the fabricated CSV sources using the method appropriate
   to your installed Zetaris edition, run a read-only smoke test:

       python3 /absolute/path/to/zetaris-getting-started/scripts/query_zetaris.py "SELECT 1"

5. Run the live six-source probe with the **actual** namespace and case ID:

       python3 -m apps.careflow.tb_zetaris_probe \
         --namespace YOUR_TEAM_NAMESPACE \
         --case-id YOUR_SYNTHETIC_CASE_ID \
         --helper /absolute/path/to/zetaris-getting-started/scripts/query_zetaris.py

Run from the TB-CareOS repository root; set PYTHONPATH=src if needed for the
legacy tests. The probe uses the Zetaris helper's own environment loading and
runs under the current Python interpreter. No shell execution is used.

If the UI returns an unfamiliar result format, the adapter fails closed with
invalid_response; capture a **redacted** response shape locally before
updating the parser. Do not treat an HTTP error or unavailable table as a
successful empty result. A genuine query is required before claiming E01 GO.

## Verification and limits

    python3 -m unittest discover -s tests -v

The probe is **not yet CareFlow evidence_bundle.v1 reconciliation**: it is
one step toward E01/E02. Only successful, real Zetaris retrieval of fabricated
screening, lab and follow-up rows can close E01. No clinical conclusions follow
from missing administrative documents; the result always requires human review.

This build reuses the official Zetaris starter **as an external tool**; do not
commit a vendor copy or reveal secrets in traces/commits.
