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


## Targeted repeat on the failing two cases — 23 October 2026

Participant reran `CASE-TB-002` and `CASE-TB-007` twice each on
retrieved and validated synthetic evidence.

| Metric | Observed |
|---|---:|
| Cases with validated source reads | 2/2 |
| Hosted model calls | 8 |
| All accepted calls | 6/8 (75%) |
| CaseLens accepted | 2/4 (50%) |
| NextStep accepted | 4/4 (100% in this small repeat) |
| Full linked chain accepted | 2/4 trials |
| Provider/model failures | 2 |
| Source writes / follow-up queries executed | 0 / 0 |

CASE-TB-002 succeeded for both CaseLens and NextStep **in both trials**,
recovering from its initial CaseLens failure. CASE-TB-007 failed CaseLens
in **both** trials, while NextStep independently passed in both. The
precise CaseLens rejection category was
`caselens_unretrieved_citation`. This means the model explanation
contained a record-shaped identifier outside the retrieved evidence
allowlist; it does not establish whether the model hallucinated one or
simply repeated an unresolved source link.

### Safety-preserving prompt mitigation (implemented; real rerun pending)

The CaseLens prompt previously exposed raw link-target IDs from source
metadata under `evidence[].links`, even when no record for that ID was
retrieved. In an administrative cross-source mismatch, a dangling
`order_id` or `result_id` may thus be echoed by the model as if
it were a cited retrieved event. That is a plausible explanation for
the CASE-TB-007 failure, **not proven from the result JSON alone**.

We have now changed CaseLens prompt construction to include only
`retrieved_links` with target IDs already observed in the evidence,
and `unretrieved_link_fields` naming dangling fields **without their
unretrieved target values**. The model is explicitly told to describe
the field-level mismatch without inventing or echoing unreturned IDs.
The strict record/subject citation validator and mandatory human
approval remain unchanged.

Regression tests verify that an unmatched target ID is absent from
the model input, that a synthetic explanation citing the unreturned
target still **fails closed**, and that existing subject-mismatch
citations still work. Both GitHub CI suites passed on the prompt
mitigation commit. **No claim of improved live CASE-TB-007 reliability
until the participant reruns the hosted model.**

Next recommended live check: `CASE-TB-007` with `--repeats 2`,
at most four hosted model calls. Inspect the new safe error categories
and linked-chain metric. Keep the original failure counts in the
submission evaluation appendix as pre-mitigation results.

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
