# TB-NextStep — E05 bounded verification planner

**Status (22 Oct 2026):** E05 post-kickoff implementation, stacked on the
E04 CaseLens branch. The prebuild was schema + CLI placeholder only.
GitHub CI tests use **no live NVIDIA or Zetaris endpoints**; a live WSL2
verification must be run separately before claiming complete E05 integration.

## Role, input, output

NextStep accepts an existing evidence_bundle.v1 from CareFlow and an
optional explanation_report.v1 from CaseLens. It emits the existing
verification_plan.v1 JSON contract (no schema changes).

- CareFlow supplies the findings and source record IDs; NextStep does not
  invent additional findings or infer medical outcomes.
- Deterministic code creates candidate lookups only in allowlisted evidence
  tables that the source checks report as available or not_found.
- NVIDIA **Nemotron 3.5 Lightning** (default) may choose **only candidate
  query IDs**, not arbitrary SQL, new record identifiers or new actions.
- An independent Python critic verifies the final assembled plan; invalid
  model choices fail closed. No silent mock/offline fallback.
- The final two actions are **manual_review** and **stop**, regardless of
  model selection. Nothing is executed by the planner.

The prebuilt v1 schema allows at most **six** actions. With mandatory
manual-review and stop actions, the effective read-only query cap is
**four** (default three), even though the original schema's max_queries
field permits five. This implementation enforces the stricter bound.

**Important:** read_only_source_query represents a proposal, not a SQL
command and not a performed retrieval. Source status not_found does
**not** mean a service or patient follow-up was missed. Source statuses
error, permission_denied and temporarily_unavailable are never
automatically retried. No patient outreach, database writes, diagnosis,
treatment recommendation, autonomous approvals or unbounded loops.

## Independent offline demo (no NVIDIA, no Zetaris)

From the repository root (after switching to the E05 branch):

    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.nextstep \
      --case-id CASE-TB-018 \
      --bundle tests/fixtures/tb_case_018_bundle.json \
      --offline \
      --output outputs/e05_case_tb_018_offline.json

The explicit --offline flag selects a deterministic-only baseline. It
does not claim NVIDIA inference.

## Live Nemotron from a saved synthetic fixture

Export your personal key in the local WSL terminal without showing it:

    read -rsp "NVIDIA API key (hidden): " NVIDIA_API_KEY
    echo
    export NVIDIA_API_KEY

    PYTHONPATH=src:. python3 -m apps.nextstep \
      --case-id CASE-TB-018 \
      --bundle tests/fixtures/tb_case_018_bundle.json \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --output outputs/e05_case_tb_018.json

## Full live evidence read + optional CaseLens report

The official Zetaris helper in ~/zetaris-getting-started must already
work with your locally configured, authorized TBCARE_OS namespace.

    PYTHONPATH=src:. python3 -m apps.nextstep \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --explanation outputs/e04_case_tb_018.json \
      --output outputs/e05_case_tb_018.json

--explanation is optional; if supplied, its case ID, findings and
evidence citations must match the CareFlow bundle. No free-form
explanation text is put into the model selection prompt.

The output file stays in gitignored outputs/ with mode 0600.
Neither ground-truth holdouts nor fake retry labels are included in
queries, prompts, or plans.

## Honest limitations / future E06–E07

- The plan is **not execution**; no follow-up verification result exists
  until an authorized human performs a separate read.
- CaseLens explanations currently do not flow into Meterless history,
  and NextStep plans are not yet stored as Meterless audit events.
- A semantic/reasoning model may choose a suboptimal query ordering.
  The strict critic blocks unauthorized operations but does not certify
  optimality. Evaluate query utility on held-out cases **post hoc only**.
- Source-check retry and visibility simulation are not implemented.
- Cross-case performance and repeated provider availability still need
  independent testing. Use fabricated administrative records only.
