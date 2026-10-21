# Candidate 1: TB-CareFlow — cross-source reconciliation

**User:** Puskesmas TB coordinator/data administrator.  
**Problem:** Inconsistent or incomplete administrative records across separate fabricated sources.  
**Unique behavior:** Query Zetaris, match subject/order IDs and event timestamps, distinguish missing documentation from a temporarily unavailable source, create an evidence-linked exception ledger.  
**Input:** synthetic CSV or case ID. **Output:** `evidence_bundle.v1`.  
**Evaluate:** exception precision/recall, matching accuracy, cited-source completeness and false alarms.

**21 Oct status:** old generic deterministic CLI works; TB-v1 Zetaris adapter is **not implemented**. Track mapping must be confirmed.
