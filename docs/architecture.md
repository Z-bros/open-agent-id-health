# Architecture v0 — problem neutral

```mermaid
flowchart TD
    A[Approved synthetic case] --> B[Query records]
    B --> C{Record available?}
    C -- No --> D[Bounded retry]
    D --> C
    C -- Yes --> E[Verify identifiers]
    E --> F{Mismatch?}
    F -- Yes --> G[Discrepancy + evidence trace]
    F -- No --> H[Verified record trace]
    C -- Retry exhausted --> G
    G --> I[Human review package]
    H --> I
    I --> J[Human approval required]
```

The agent is **deterministic only at present**. Zetaris and Meterless are placeholders, not functioning integrations.
Unavailability is not proof of clinical or administrative wrongdoing. No autonomous patient routing, treatment, claims decisions or messaging.
