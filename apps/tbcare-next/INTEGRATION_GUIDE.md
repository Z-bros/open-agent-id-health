# TBCare — Next.js design integration and local verification

> **Repository update (25 Oct 2026):** This source now lives in `apps/tbcare-next/` on the consolidated integration branch. GitHub Actions completed the four static suites, TypeScript typecheck, and production demo-mode build successfully; genuine sponsor-connected WSL clean-clone acceptance remains separate. Historical package-handoff notes below may predate this repository integration.

**Scope:** Optional frontend based on the uploaded `tb-careos-agentic-starter(2).zip`, adapted to the current TBCare prototype and Phase G application activity API. It is **not a replacement for the existing Python backend** or an official TB health information integration.

## Why keep this as a separate frontend?

The working product already serves a trustworthy localhost-only Python interface on `127.0.0.1:8765` with carefully tested Zetaris queries, deterministic CareFlow reconciliation, independently validated Nemotron agents, a local human-review note ledger, and a separate persisted Meterless audit viewer. This starter is **Next.js 15 / React 19**; replacing the existing Python HTML app would add an unnecessary bundling/runtime dependency near the hackathon deadline. An opt-in frontend gives us the new case-explorer, investigation and bilingual design without changing those backend contracts.

## Visual changes incorporated from the supplied starter

- Preserved the **case explorer with a 36-ID table** (only three fixtures load in demo), filters, selected-case summary and separate investigation layout.
- Preserved **English/Bahasa Indonesia** interface strings, on-demand separate CaseLens and NextStep panels, a human checkpoint, in-app notices, source/citation provenance and local reviewer-note form.
- Preserved **separate view semantics**: `CASE-TB-001` has no finding, `CASE-TB-009` shows unreturned lab-result documentation, and `CASE-TB-018` has a subject-reference mismatch.
- Renamed the visible product to **TBCare**, removed the decorative hospital/lungs logo, dark/blue gradient patterns and remote font imports, and styled the workbench with restrained teal, green, white, and warm review amber. No Kemenkes, SITB or SATUSEHAT official logo/endorsement is claimed.
- Changed **accepted model outputs** from celebratory green to **amber “Validated · Review needed”** for unresolved case discrepancies. NextStep stays proposed/not executed. No-finding paths remain non-clinical.
- Fixed the uploaded demo loader bug: `fixtureBundles` is now imported for actual evidence, while the allowlisted case IDs remain separate.
- Aligned human-review note max length to the Python backend (12–280 characters), preserving exact evidence snapshot and idempotency fields.
- Added a read-only view of actual **Phase G `/api/cases/{id}/activity`** server milestones in local mode; this is distinct from the browser notification inbox and the persisted Meterless audit. Polling occurs only while the tab is visible and an investigation is open. No background worker, browser push, automatic source query, or live private model thinking is claimed.
- Tightened the optional localhost bridge: exact same-origin POSTs, allowlisted synthetic routes, mandatory evidence digest, review intent, bounded JSON review content, and no arbitrary proxy URL.

## Install alongside existing repo

Download the `TBCare_Integrated_Next_Frontend.zip` and extract it **at the repository root**. It contains `apps/tbcare-next/` and this integration guide; it will **not overwrite** `apps/product`.

### Demo-first run (no backend or NVIDIA key required)

From WSL (internet access for `npm install` is necessary):

```bash
cd apps/tbcare-next
npm install
npm run test:static
npm run test:agentic
npm run test:integration
npm run typecheck
npm run build
npm run dev
```

Visit **http://127.0.0.1:3000**. By default the frontend uses its **clearly labelled offline UI fixtures**, with intentionally simulated model results. This is not a demonstration of live Zetaris/NVIDIA/Meterless integration. The current Python frontend remains at port **8765** if running.

### Actual localhost Python API mode

**Terminal A:** start your trusted existing Python TBCare application as before. From repository root:

```bash
PYTHONPATH=src:. python3 -m apps.product \
  --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
  --namespace TBCARE_OS \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --review-dir outputs/reviews \
  --activity-dir outputs/activities \
  --meterless-reference "$HOME/Meterless/engines/world-model/reference" \
  --meterless-state-dir outputs/meterless \
  --port 8765
```

Keep the existing `NVIDIA_API_KEY` secret **only in Terminal A's environment**. Never place that key in `.env.local` or expose it to the browser.

**Terminal B:** inside `apps/tbcare-next/`, set exactly:

```env
NEXT_PUBLIC_TBCARE_MODE=local
TBCARE_ENABLE_LOCAL_PROXY=1
```

in `.env.local`, then run `npm run dev`. Visit **http://127.0.0.1:3000**. The server adapter connects **only** to the local Python endpoint at `http://127.0.0.1:8765` and restricts supported paths. An explicit CaseLens/NextStep click invokes the real backend with the current SHA256 evidence snapshot, subject to its independently enforced validation and refusal rules. No provider credentials are sent by the browser.

### Acceptance checks before design signoff

1. Open `CASE-TB-001`, `009`, `018` and confirm only observed/synthetic information is shown as such.
2. In **demo mode**, 009 CaseLens rejection remains rejected and 018 results are clearly **simulated**; audit history shows no fabricated Meterless events.
3. In **local API mode**, accepted model outputs display **review required** and plans remain **not executed**; failure modes do not imply invalidated evidence or missed clinical care.
4. The local activity index (real Phase G server events), browser session notices, fictional local review notes and actual persisted Meterless history must remain clearly separate.
5. Inspect citations against source IDs and ensure a changed evidence snapshot forces re-retrieval.
6. Record a test review note with all three human confirmations and 12–280 characters. Confirm the record returns from backend review history; no official action occurs.
7. Exercise keyboard and mobile/table horizontal scrolling, the English/ID switch, the active navigation item, and the focus ring.
8. Validate security after future edits; never expose the optional proxy on a public URL.

## Validation completed in this environment

- `npm run test:static` — **passed**.
- `npm run test:agentic` — **passed**.
- `npm run test:integration` — **passed**.
- `npm run typecheck` / `npm run build` — **not validated** because Next/React/lucide Node modules were absent and npm registry access unavailable here. Their absence produces module-resolution errors and is not evidence of a clean successful build.
- Live browser walkthrough with genuine backend — **not yet verified**.

This output is a tested **source-code integration package**, not a production deployment, not a merged GitHub PR and not a verified public-health data integration. Do not submit it as live-agent evidence without the local connected-mode acceptance checks above.


## v0.3.1 local-mode and typecheck correction

Version 0.3.1 corrects the TypeScript error in `app/page.tsx` when incrementing a
`Record<string, number>` local review-note count. It also replaces two
`align-items:end` rules with the interoperable `flex-end` value.

`GET /` returning 200 from Next.js only means that the frontend is running.
It is *not* a public deployment and does *not* verify Python, Zetaris or NVIDIA.

Check Python first: `curl -i http://127.0.0.1:8765/api/cases`. In
`apps/tbcare-next/.env.local` set both `NEXT_PUBLIC_TBCARE_MODE=local` and
`TBCARE_ENABLE_LOCAL_PROXY=1`, then completely restart Next.js on localhost.
Check `curl -i http://127.0.0.1:3001/api/backend/cases`; only a 200 with the
case inventory verifies the bridge. Check the UI ribbon says connected.
Selecting a case triggers *real read-only synthetic* Zetaris retrieval; the
explicit explanation and verification buttons call hosted Nemotron through
Python, with safe validation failures still possible. Do not paste secrets into
Next .env files. For 403/503 check the error code and localhost processes.

Dependency-based `npm run typecheck` and `npm run build` must still be run by
the local user. The source-level tests do not substitute for this.
