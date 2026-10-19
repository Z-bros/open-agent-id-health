# Sponsor integration plan — source reviewed 19 Oct 2026 (not yet connected)

Official source repositories supplied by project owner:
- Zetaris: https://github.com/zetaris/getting-started
- Meterless: https://github.com/Meterless/Meterless

Status: documentation verified; no actual runtime integration or credential verification yet. Follow the event's orientation PDF / HackOS official rules for deadlines and judging; the Meterless repository's hackathon guide contains different dates/rubric and may be stale.

## Zetaris — federated access / SQL
Source: `START-HERE.md`, `docs/connections/README.md`, `scripts/HOWTO.md`.

Zetaris serves as the data query layer for synthetic TB screening, diagnostic order/result and SITB-like follow-up tables. **Do not claim access to official SITB or patient data.**

Available access paths:
1. Event/shared instance with provided UI URL, account, query permission, team prefix.
2. Own Zetaris installation.
3. Query using SQL Editor first; later integrate with Python helper or authorized REST/JDBC.

First read-only smoke tests from official guide:
```sql
SELECT 1 AS one;
SHOW LIGHTNING DATABASES;
SHOW LIGHTNING TABLES NY_TAXI;
SELECT * FROM NY_TAXI.taxi_zones LIMIT 5;
```
Shared samples may vary by permission. Never create objects in the shared environment without assigned team ownership and explicit approval.

Python client scripts from the Zetaris repository:
```bash
python3 scripts/check_zetaris.py
python3 scripts/query_zetaris.py "SELECT 1"
```
These helpers route through the UI proxy, not a raw API URL. The official repo's `.env.local` uses `ZETARIS_BASE_URL` (UI origin), `ZETARIS_ORG_ID`, `ZETARIS_API_KEY` or username/password; optional query limit and engine ID. Raw REST/JDBC use separate configurations.

## Meterless — World Model for persistent case state, NOT an assumed LLM API
Source: `Meterless/Meterless/engines/world-model/README.md` and `reference/README.md`.

Proposed functional role: append-only, provenance-traceable synthetic case events and investigation transitions, reproducible case timeline, safe replay/idempotency, and staff-review state. Pair with **separate** deterministic checks or a selected LLM for semantic investigation; do not misrepresent World Model as an inference endpoint.

World Model reference is TypeScript, with a runnable local test suite (not production-ready). Potential approach: Node/TypeScript state sidecar to our Python workflow, or port compatible contracts after validating license and conformance.

Reference smoke test after cloning the Meterless repo:
```bash
cd engines/world-model/reference
npm install
npm test
npx tsx scripts/idempotency-check.ts
```
Do not assume `METERLESS_API_KEY` or `METERLESS_ENDPOINT` exists for World Model. Nightshift's model-provider mode is separate and hardware dependent.

## Cursor + Space XAI
Develop the hackathon implementation in Cursor and document Space XAI participation using HackOS guidance. The Zetaris repo includes `docs/connections/cursor-connection.md`.

## Acceptance / owner actions
- [x] Review official source repos and distinguish product roles
- [ ] Confirm Zetaris instance URL / organization ID / assigned team namespace and query rights (do not paste passwords/keys)
- [ ] Zetaris `SELECT 1` returns a real row in permitted instance
- [ ] Confirm Node.js/npm environment and Meterless World Model reference test passes
- [ ] Choose integration boundary for Python ↔ TypeScript
- [ ] Confirm Cursor + Space XAI configuration in HackOS
- [ ] During build window: run a synthetic cross-source Zetaris query and World Model audit replay
- [ ] Demonstrate documented sponsor contributions in demo

Keep all secrets local; use gitignored `.env` / `.env.local`, never issues or transcripts.
