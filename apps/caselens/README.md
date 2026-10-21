# TB-CaseLens — explain

**Prebuild status:** specification, schema and `--help` CLI placeholder only. No LLM inference or evidence explanation occurs yet.

```bash
python -m apps.caselens --help
```

Build-window input: saved `evidence_bundle.v1` with cited synthetic source records (CareFlow need not be online for independent testing). Output: `explanation_report.v1` with *supported / contradicted / unresolved* administrative hypotheses and the supporting `record_id` values.

The eventual inference adapter must use an authorized provider, not assume the Meterless World Model exposes a chat-completions endpoint. Do not infer medical outcomes from missing electronic evidence.
