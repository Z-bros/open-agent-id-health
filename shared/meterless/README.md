# Meterless World Model adapter — not implemented yet

Upstream `Meterless/Meterless/engines/world-model/reference` passed 10/10 tests and idempotency replay on the participant's WSL2 machine. This verifies **the reference engine**, not TB-CareOS case ingestion.

Build-window plan: establish Python ↔ TypeScript transport, append synthetic events with stable identifiers/provenance, replay without duplicates and inspect supersessions/conflicts in audit history. Do not claim this module supplies an LLM inference API.
