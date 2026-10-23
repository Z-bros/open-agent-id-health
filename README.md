# TB-CareOS — Indonesian TB evidence investigation (monorepo)

> **Product checkpoint (23 Oct 2026):** TB-CareOS is a working localhost synthetic administrative investigation product using real read-only Zetaris, hosted Nemotron CaseLens/NextStep, and genuine read-only Meterless event history. Product Phases A–C were verified in the participant's browser, including local fictional review notes (separate from Meterless). E09 verified 36/36 deterministic synthetic contract/workflow checks; E10 observed 8/10 live hosted response acceptances in a representative six-case sample, with CaseLens failures explicitly reported and rejected by strict critics. **Product Phase D adds a guided investigation journey and honest case-list source states; participant browser verification is pending.** This is not production/clinical software, does not contact patients or execute planned checks, and does not imply official case approval. See [interactive product](apps/product/README.md), [E09 verification](docs/e09-verified-evaluation-results.md) and [E10 reliability results](docs/e10-verified-nemotron-results.md). Historical prebuild material below remains for disclosure.

**Prebuild status, 21 October 2026:** repository structure and JSON contracts prepared before the official hackathon build window (22 Oct 00:00 UTC / 07:00 WIB). These are **not** three finished agents or submissions. [Pre-existing work disclosure](docs/prebuild-disclosure.md).

TB-CareOS explores **administrative follow-up evidence discrepancies** for Indonesian Puskesmas TB coordinators, using **entirely fabricated** screening, laboratory and follow-up records. It does **not** connect to SITB/SATUSEHAT, diagnose, prescribe, contact patients, or assert that a missing digital record means missed care.

## Three independently testable candidate apps

| App | Independent purpose | State before kickoff |
| --- | --- | --- |
| [CareFlow](apps/careflow/README.md) | Reconcile separate record sources; flag mismatches and missing/unavailable evidence | Old deterministic generic prototype works; TB Zetaris integration planned |
| [CaseLens](apps/caselens/README.md) | Investigate *why* a mismatch is flagged; cite evidence and uncertainty | Design and CLI placeholder only |
| [NextStep](apps/nextstep/README.md) | Decide permitted next evidence query or human escalation using bounded planner/critic | Design and CLI placeholder only |
| [Dashboard](apps/dashboard/README.md) | Unified human-review interface | Design only |

The intended flow is **CareFlow → CaseLens → NextStep → staff review**. Every app should also support **standalone evaluation from a saved synthetic evidence bundle**, independently of other running app services. See [system architecture](docs/architecture.md) and [shared contracts](shared/README.md).

### Repo map

```text
apps/
  careflow/               Legacy CLI wrapper and future reconciliation API
  caselens/               Planned evidence explanation agent
  nextstep/               Planned bounded verification planner
  dashboard/              Planned staff-review UI
shared/
  contracts/              v1 JSON message schemas and example fixtures
  zetaris/                Planned read-only source adapter
  meterless/              Planned World Model state/audit adapter
  inference/              Planned authorized Nemotron/provider adapter
src/healthagent/          Preserved original Python package, CLI, tests
data/synthetic/           Existing tiny prototype fixture; new TB v1 is separate ZIP
tests/                    Existing five regression tests + contract checks
docs/submissions/         Candidate submission boundaries, not eligibility proof
```

### Existing working demo (unchanged)

Requires Python 3.10+:

```bash
python -m pip install -e .
healthagent --list
healthagent --case CASE-TB-CONFLICT
python -m apps.careflow --case CASE-TB-CONFLICT
python -m unittest discover -s tests -v
```

Existing `data/synthetic/records.json` includes earlier generic non-TB cases. Its CLI and tests are intentionally retained. `python -m apps.caselens --help` and `python -m apps.nextstep --help` show only *placeholder* interfaces, **not running agents**.

### Synthetic TB benchmark

The separate fabricated **36-case tb_v1 ZIP** was prepared on 21 Oct and distributed to the participant. It was **not imported to this GitHub repository by this structural commit**. Extract it under `data/synthetic/tb_v1/` (keep its manifest, schema, verification script and disclosure). The `ground_truth_holdout.csv` must not be an agent input. See [data instructions](data/synthetic/README.md).

### Integration readiness is not application integration

- **Zetaris:** local Docker platform installation passed 9/9 verification checks and queried sample rows; no TB dataset ingested yet.
- **Meterless World Model:** upstream TypeScript reference passed 10/10 tests and idempotency smoke check; no app-specific event adapter yet.
- **Meterless inference / NVIDIA Nemotron:** organizer-approved URL/credential/model and actual inference remain unverified. World Model is **not** an LLM.
- **Cursor:** AI workspace read and summarized repository; file generation/execution and Space XAI account status remain to verify.

### Competition and safety

Multiple entries per team and shared repository across tracks are **not yet confirmed**. Orientation previously said “one team, one track.” Treat three apps as an architecture until HackOS/organizers explicitly authorize multiple entries. Fallback: one integrated TB-CareOS entry.

See [problem decision](docs/problem-decision.md), [source evidence](docs/source-evidence.md), [sponsor plan](docs/sponsor-integration.md) and [submission plans](docs/submissions/README.md).

Use fabricated/non-identifiable data only. Human approval required for any administrative follow-up. Keep keys, real patient data and platform environment files out of Git. Final deadline per orientation: **27 Oct 23:45 UTC / 28 Oct 06:45 WIB**.
