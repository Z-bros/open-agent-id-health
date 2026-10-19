# TB-CareFlow — proposed investigation architecture

```mermaid
flowchart TD
  A[Select synthetic TB follow-up case] --> P[Plan required evidence]
  P --> Z[Zetaris: query screening, test, result, SITB-like follow-up tables]
  Z --> V[Normalize IDs and inspect event sequence]
  V --> M[Meterless: critique gaps with source evidence IDs]
  M --> D{Contradiction or missing data?}
  D -- Yes --> R[Targeted re-query with bounded retry]
  R --> E{Resolved?}
  E -- No --> H[Escalate uncertain case to coordinator]
  E -- Yes --> O[Auditable reconciliation result]
  D -- No --> O
  O --> U[Human reviewed worklist]
  H --> U
```

**This is intended architecture, NOT proof of sponsor integrations.** Existing Python pre-hackathon implementation is deterministic and generic; Zetaris and Meterless interfaces are unimplemented.

Target user: Puskesmas TB programme coordinator. Target task: exception investigation across synthetic screening, diagnostic and documented follow-up events.

Human clinician/coordinator must approve real-world follow-up, communications or changes to SITB. A missing event can mean data delay; it must not be equated with missing care or nonadherence.
