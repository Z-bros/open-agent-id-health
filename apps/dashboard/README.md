# TB-CareOS E06 — local human-review dashboard

**Post-kickoff implementation (22 October 2026), stacked on E05.**
The prebuild version was design notes only. E06 generates a self-contained
local HTML report from the **fabricated** CareFlow, CaseLens and NextStep
contracts. It is a **read-only review display**, not a server, clinical
decision tool, official registry, or approval/communication service.

## Visible panels

1. Overview with per-case counts and clear human-review requirement.
2. Latest observed status of each of five Zetaris evidence source tables.
3. CareFlow rule-based discrepancy cards with exact supporting business IDs;
   when supplied, CaseLens bounded Nemotron explanation and unresolved questions.
4. NextStep proposed read-only source checks, manual review and terminal stop.
   Proposed source checks are clearly marked **not executed**.
5. Evidence timeline with UTC timestamps, business event IDs, source row
   provenance and invented subject identifiers.
6. Optional Meterless reference summary of events, observations, and audit
   count from a **separate prior run**. No fabricated audit claim is shown
   when no summary was provided.

The HTML contains **no JavaScript**, external images, fonts or requests.
It includes a restrictive Content-Security-Policy and escapes untrusted model
and source text. The viewer itself never invokes a model or follows any
proposed source query.

## Setup and offline demo

From repository root in Ubuntu WSL2:

    git fetch origin
    git switch --track origin/feat/e06-local-review-dashboard
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Build a stand-alone dashboard using only the saved synthetic fixture:

    PYTHONPATH=src:. python3 -m apps.dashboard \
      --case-id CASE-TB-018 \
      --bundle tests/fixtures/tb_case_018_bundle.json \
      --output outputs/e06_case_tb_018.html

Open the report in Windows from WSL2:

    explorer.exe "$(wslpath -w outputs/e06_case_tb_018.html)"

The last command opens an HTML file only; it starts no listening service.

## Integrated E04 + E05 + live read-only Zetaris demo

Re-use the already-generated E04 CaseLens JSON and E05 NextStep JSON:

    PYTHONPATH=src:. python3 -m apps.dashboard \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --explanation outputs/e04_case_tb_018.json \
      --plan outputs/e05_case_tb_018.json \
      --output outputs/e06_case_tb_018.html

    explorer.exe "$(wslpath -w outputs/e06_case_tb_018.html)"

This mode re-queries the five authorized synthetic Zetaris source tables
**once** via the existing read-only CareFlow adapter. It validates the
optional explanation and plan against those currently retrieved records.
If an input disagrees with the requested case or evidence citations,
dashboard generation fails closed. No NVIDIA call is made by E06 itself.

## Optional real Meterless E03 summary

The existing E03 command prints a JSON summary. To capture it in an
ignored local file:

    REFERENCE="$HOME/Meterless/engines/world-model/reference"

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --reference "$REFERENCE" \
      --state-dir outputs/meterless > outputs/e03_case_tb_018.json

Then append this option to the above E06 command:

    --meterless-summary outputs/e03_case_tb_018.json

This uses the actual Meterless reference sidecar. The viewer shows
**only verified summary counters** and explicitly states that E03 currently
persists source evidence and CareFlow findings; CaseLens explanation and
NextStep plan audit events are a separate upcoming integration.

## Boundaries and honest limitations

- Use only fabricated CASE-TB-* records. NEVER ingest held-out oracle labels,
  real patient data, SITB/SATUSEHAT records, or credentials.
- Source checks marked not_found do **not** imply missed care.
- Proposed NextStep lookups have **not been executed**, and the UI has no
  auto-approve, messaging, prescription, mutation, or clinical operations.
- The output file is written with mode 0600 in the local gitignored outputs
  directory (Windows mount permissions may differ). Do not publicly host
  the HTML without separate privacy/security review.
- This is a one-case static report, **not yet** a live updating case queue or
  staff case management system.
- It is not proof of source completeness, LLM factuality, case matching
  accuracy across all 36 synthetic cases, or official service readiness.
- Independently evaluate E06 offline, then use the local WSL workflow before
  claiming integrated participant verification.
