# TB-CareFlow — reconcile

**Prebuild status:** working *generic* deterministic CLI in `src/healthagent/`; there is **no** live TB/Zetaris integration yet.

**Goal:** read fabricated screening, lab and follow-up events through Zetaris, reconcile identifiers and timestamps, distinguish unavailable evidence from absent care documentation, and output a source-linked `evidence_bundle.v1`.

Existing compatibility demo (after `python -m pip install -e .`):

```bash
python -m apps.careflow --list
python -m apps.careflow --case CASE-TB-CONFLICT
```

This still reads `data/synthetic/records.json`, not the separate TB v1 package or the local Zetaris server. A versioned evidence schema is in `shared/contracts/`. The authenticated SQL integration and TB-specific evaluation are build-window tasks.
