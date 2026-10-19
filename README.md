# Open Agent Indonesia Healthcare

**Pre-hackathon scaffold (19 Oct 2026). The target hospital problem is not yet selected.**

A synthetic-data-only, deterministic evidence investigation foundation for Indonesian healthcare operations. The workflow retrieves records, checks identifiers, retries unavailable sources, and prepares a traceable **human-review package**. It does not diagnose, prescribe, determine eligibility, allege fraud, or send referrals.

## Quick start
```bash
python -m pip install -e .
healthagent --list
healthagent --case CASE-DX-MISSING
python -m unittest discover -s tests -v
```

## Current capabilities
- Synthetic referral, diagnostic follow-up and TB coordination examples.
- Bounded retries, explicit missing-evidence and identifier-mismatch flags.
- Audit trace and human review requirement; five regression tests.

**Not yet built:** AI reasoning, sponsor integrations, clinical deployment, user interface, or independently validated hospital impact.

## Repository
- `src/healthagent/`: typed models, workflow, synthetic adapter, CLI, sponsor stubs
- `data/synthetic/`: fabricated cases
- `tests/`: offline regression tests
- `docs/`: problem selection, architecture, sponsor plan, demo and submission

## Competition
Build window 22–27 Oct 2026 UTC. Submission deadline **27 Oct 23:45 UTC / 28 Oct 06:45 WIB**. Required stack includes Zetaris, Meterless and development in Cursor with Space XAI, subject to official rules.

## Ethics and pre-existing work
Do not commit patient data, access credentials, or unlicensed datasets. Use `.env` locally and maintain audit trails. All clinical or operational actions require authorized human approval.

**Disclosure:** This scaffold was prepared **19 October 2026, before the official 22 October build window**. Declare it as pre-existing at submission. Do not claim it as hackathon-window implementation.

The project name, final track, license and hospital workflow will be determined after evidence review.
