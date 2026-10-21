# Shared components — prebuild contracts

The three candidate agents exchange **versioned JSON values**, rather than directly importing one another's internals.

| Message | Producer | Consumer |
| --- | --- | --- |
| `evidence_bundle.v1` | CareFlow | CaseLens, NextStep, UI |
| `explanation_report.v1` | CaseLens | NextStep, UI |
| `verification_plan.v1` | NextStep | UI / human coordinator |

Schemas and minimal fabricated test examples live in `contracts/`. They are **design contracts**, not existing HTTP endpoints.

Planned adapter boundaries: [Zetaris](zetaris/README.md) for real SQL queries on *synthetic TB data*; [Meterless World Model](meterless/README.md) for event provenance/state; [inference provider](inference/README.md) for separately authorized Nemotron/LLM reasoning.

Preserve `case_id`, `record_id`, source-specific IDs, timestamps, source availability and evidence citations. Never give any agent the held-out ground-truth label file.
