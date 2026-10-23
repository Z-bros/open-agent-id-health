# E10 participant-hosted Nemotron result — 23 October 2026

Two participant-produced JSON reports from the actual local synthetic
Zetaris / hosted NVIDIA Nemotron 3.5 Lightning run were independently checked.

## Representative six-case run

| Metric | Observed |
|---|---:|
| Synthetic cases with validated five-table source reads | 6/6 |
| Model API calls | 10 |
| Accepted agent responses (passed existing validators) | 8/10 (80%) |
| Rejected agent responses | 2/10 (20%) |
| CaseLens accepted | 3/5 (60%) |
| NextStep accepted | 5/5 (100% for this sample) |
| Fully linked CaseLens-then-NextStep success on a finding-bearing case | 3/5 |
| No model needed, CASE-TB-001 | 2 agent operations |
| Source writes / suggested checks executed | 0 / 0 |
| Holdout ground-truth read by agents | No |

## Case outcomes

| Case | Administrative category | CaseLens | NextStep |
|---|---|---|---|
| CASE-TB-001 | No rule-based finding | No model needed | No model needed |
| CASE-TB-002 | Duplicate business event replay | Rejected | Accepted independently |
| CASE-TB-004 | Follow-up document not returned in query | Accepted | Accepted |
| CASE-TB-007 | Cross-source link mismatch | Rejected | Accepted independently |
| CASE-TB-009 | Lab document not returned in query | Accepted | Accepted |
| CASE-TB-018 | Subject mismatch | Accepted | Accepted |

Both CaseLens failures were recorded under the coarse original category
`grounding_or_contract_rejection`. This does **not** reveal which exact
critic rule was violated, nor prove that the model hallucinated a record.
The model output was *not accepted*. On both failed cases, NextStep still
generated a bounded plan against the original verified CareFlow evidence,
but the full linked explanation-plus-plan chain **did not succeed**.

The separate single-case smoke test for CASE-TB-018 passed both model calls
(2/2). CASE-TB-018 also passed in the six-case batch; neither run establishes
broad reliability from such a small sample.

## Next corrective iteration

- **Diagnostic change:** E10 now records the exact allowlisted critic rule
  category (e.g., `caselens_missing_business_citation`,
  `caselens_invalid_json`), never raw provider/model text or tokens.
  New linked-chain counters distinguish success of both agents together
  from a NextStep plan generated when CaseLens output was rejected.
- **Targeted repeat:** rerun CASE-TB-002 and CASE-TB-007 with
  `--repeats 2`, on the same retrieved synthetic evidence per case.
  This produces at most 8 actual provider calls. Examine which rule is
  rejected; do not relax citations or approval constraints.
- **Mitigation if needed:** adjust only the model output-instruction
  prompt to improve compliance (all required record IDs, neutral wording,
  strict JSON). Keep the deterministic grounding critic unchanged.
- **Demo:** prioritize validated successful CASE-TB-001, 009, 018.
  Explicitly demonstrate fail-closed behavior on a rejected output.

## Evidence scope and limitations

E09 tested 36/36 deterministic source/citation/workflow contracts and made
zero LLM calls. E10 tested a *purposively selected* six-case hosted sample
with one trial each; **80% is observed output contract acceptance, not a
reliable population estimate, and not clinical or explanation accuracy**.
Zero writes and human approval preserved; no real patients or holdout
labels were included. Model outputs and secrets were not stored.

Participant report filenames:
`e10_case018_live.json`, generated 2026-10-23 03:24:54 UTC;
`e10_representative_live.json`, generated 2026-10-23 03:25:36 UTC.

The two original files are user-supplied local artifacts; this tracked
documentation stores only synthetic aggregate and categorical results.
