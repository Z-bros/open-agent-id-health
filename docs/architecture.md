# TB-CareFlow — intended sponsor architecture (not yet implemented)

```mermaid
flowchart TD
  A[Select synthetic TB record bundle] --> Z[Zetaris: query screening, lab and SITB-like records]
  Z --> N[Python: normalize identifiers and event timestamps]
  N --> W[Meterless World Model: append provenance-linked events and maintain case state]
  W --> V[Verifier: evidence checks and possible separate LLM review]
  V --> D{Missing or conflicting records?}
  D -- Yes --> R[Bounded query retry and inspection]
  R --> W
  D -- No --> Q[Reviewed evidence summary]
  V --> H[Unresolved exceptions to coordinator]
  H --> Q
  Q --> U[Human-reviewed follow-up worklist]
```

**Sponsor role correction (19 Oct 2026):** Meterless World Model supplies event-sourced state, identity resolution and provenance. It is **not** automatically an LLM evaluator. Semantic critique, if added, will be a separate agent component with independent validation; do not imply an LLM model is supplied merely by importing a World Model reference.

Proposed integration boundary: Python CLI and deterministic validation + Zetaris queries; TypeScript Meterless World Model reference as local service/process. Verify compatibility with the official source docs before implementation.

Current code is generic synthetic deterministic scaffold only. All new runtime work is pending the official build window. No real patient data, autonomous clinical actions, official SITB connection, or unapproved outreach.
