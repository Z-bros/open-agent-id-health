# E08 — Meterless audit for CareFlow, CaseLens and NextStep

**Status:** E08 backend implementation is stacked on E06. E03 originally archived
only source-linked CareFlow observations and rule-based findings. E08 optionally
archives validated E04 explanation reports and E05 verification plans as
agent-sourced observations in the real Meterless World Model reference.

## Important semantics

- CaseLens explanation reports are records of an agent-generated explanation,
  not clinical conclusions or human decisions.
- NextStep plans are proposals, **not executed actions**. They contain the
  explicit execution_status value not_executed, human review and terminal stop.
- Each agent report has a replay-stable, per-case external ID. If its text
  changes, Meterless may append an updated event under the same identity.
- E08 uses the latest synthetic source observation timestamp to anchor the
  archived evidence snapshot consistently. This timestamp is NOT the time
  Nemotron ran or a reviewer made a decision.
- The adapter rejects foreign-case reports, dangling citations, unsupported
  plan operations and common clinical claims before invoking Meterless.
- Source snapshots, real patient data, held-out ground-truth labels,
  credential files, automated outreach and writes to official systems are
  never inputs.

## WSL2 end-to-end demonstration

Start from the repository root and fetch the E08 branch:

    git fetch origin
    git switch --track origin/feat/e08-meterless-agent-audit
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Reuse the two already-verified local E04/E05 reports:

    REFERENCE="$HOME/Meterless/engines/world-model/reference"

    PYTHONPATH=src:. python3 -m apps.careflow.tb_meterless \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --explanation outputs/e04_case_tb_018.json \
      --plan outputs/e05_case_tb_018.json \
      --reference "$REFERENCE" \
      --state-dir outputs/meterless > outputs/e08_case_tb_018.json

Read the summary:

    python3 -m json.tool outputs/e08_case_tb_018.json

When the underlying case evidence was already archived by E03, the first
E08 run should add two agent report observations. Repeating the **same inputs**
should append zero duplicate events. If the E04 report text changes, that is
a changed report, not a duplicate under identical content.

Regenerate the E06 dashboard with the real E08 summary:

    PYTHONPATH=src:. python3 -m apps.dashboard \
      --case-id CASE-TB-018 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --explanation outputs/e04_case_tb_018.json \
      --plan outputs/e05_case_tb_018.json \
      --meterless-summary outputs/e08_case_tb_018.json \
      --output outputs/e06_case_tb_018.html

    explorer.exe "$(wslpath -w outputs/e06_case_tb_018.html)"

## Audit limitations

GitHub CI uses the actual Meterless reference and must demonstrate append
and cold-start deduplication. Source entity derived projections may be rebuilt
on reload without new persisted events; we do not claim exact state canonical
equality across process restarts. The currently exposed CLI reports audit
counts, not a complete interactive audit-event browser.

This remains backend engineering. An interactive case explorer, live API,
review queue and audit UI are required separately for the product milestone.
See docs/product-mvp-roadmap.md.
