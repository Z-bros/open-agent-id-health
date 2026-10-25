# E09 participant-verified evaluation results — 23 October 2026

**Status:** Participant executed the 3-case and full 36-case E09 evaluations
against their locally configured synthetic `TBCARE_OS` Zetaris namespace
and provided both exported JSON reports. The findings below were
independently recalculated from those exports, not inferred from CI fixtures.

## Full 36-case evidence integrity report

| Metric | Observed |
|---|---:|
| Cases requested / accounted for | 36 / 36 |
| Cases evaluated with validated deterministic offline plans | 36 |
| Fully query-readable cases in the evaluator's sense | 36 |
| Source access impaired | 0 |
| Zero-evidence cases blocked | 0 |
| Contract / read validation failures | 0 |
| Retrieved observations | 163 |
| Total first-pass read checks (5 x 36) | 180 |
| Successful nonempty source checks | 161 |
| Successful empty query checks (`not_found`) | 19 |
| Cases with one or more administrative findings | 21 |
| Cases with no findings on this read | 15 |
| Total deterministic administrative findings | 21 |
| Read-only follow-up checks *proposed but not executed* | 26 |
| NVIDIA model calls within E09 | 0 |
| Source mutations / proposed actions executed | 0 / 0 |
| Held-out ground-truth labels used | No |
| Human approval requirement preserved in valid plans | Yes |

`fully query-readable` means **no source access errors**, not that
all five tables returned data. Specifically, source results include
`lab_results:not_found` for 7 case queries and
`followup_events:not_found` for 12; these are successfully completed
queries returning zero rows. **Neither is proof of missed care, or a
verified complete source snapshot.**

### Finding category distribution

| Deterministic rule-based category | Finding count |
|---|---:|
| `lab_document_not_found_in_query` | 6 |
| `subject_mismatch` | 5 |
| `followup_document_not_found_in_query` | 5 |
| `cross_source_link_mismatch` | 3 |
| `duplicate_business_event_replay` | 2 |
| **Total** | **21** |

There were 15 cases with zero emitted findings. Absence of a rule-based
finding in a retrieved snapshot does not establish true administrative
completeness or patient clinical outcomes.

### Golden demo case agreement

| Case | Observations | Rule-based finding(s) | Proposed checks |
|---|---:|---|---:|
| CASE-TB-001 | 5 | None on this read | 0 |
| CASE-TB-009 | 3 | `lab_document_not_found_in_query` | 1 |
| CASE-TB-018 | 5 | `subject_mismatch` | 2 |

All three per-case objects in the separately produced 3-case result
match their counterparts in the full 36-case result **exactly**.

## Scope and reproducibility

The reports are labelled
`synthetic_administrative_contract_and_workflow_integrity`.
This validates real read-only source access, data/contract structure,
CareFlow citation referential integrity, human approval flags and
deterministic offline NextStep planning for the locally configured
fabricated case corpus.

**It does not measure** false positives or false negatives against the
secret synthetic oracle, precision, recall, AI model explanation accuracy,
model failure rate, completed administrative actions, patient outcomes,
reviewer authentication, or production suitability. E09 made **zero
NVIDIA model calls**. A post-hoc, separately controlled oracle comparison
could assess rule coverage later, but the oracle must remain excluded
from agent retrieval, prompts and interactive product input.

Provenance: user-supplied local exports generated 23 Oct 2026:
`e09_golden_case_integrity.json` (02:55:02 UTC),
`e09_36_case_integrity.json` (03:04:52 UTC).
The full case-level JSON remains in the participant's ignored local
`outputs/` directory; this tracked documentation includes aggregate
synthetic metrics only.
