# TB-NextStep — verify

**Prebuild status:** specification, schema and `--help` CLI placeholder only; no running planner/critic.

```bash
python -m apps.nextstep --help
```

Build-window input: `evidence_bundle.v1` plus optional `explanation_report.v1`. Output: `verification_plan.v1` with a bounded number of **read-only** source lookups, stop conditions and manual-review escalation.

No patient messaging, prescription, diagnosis, official system writes or unbounded query loops. Must be independently demonstrable using a saved synthetic evidence bundle.
