# TBCare — submission build quickstart (synthetic-only)

> Status: candidate branch `integrate/tbcareos-product-g-candidate`. This guide describes localhost software, not production, clinical, SITB or SATUSEHAT integration. **PR #23 is intentionally unmerged.** Date: 25 October 2026.

## Architecture

- **Zetaris**: read-only retrieval of five fabricated TB administrative tables in `TBCARE_OS`.
- **CareFlow**: deterministic source-linked administrative discrepancies.
- **CaseLens**: explicitly invoked NVIDIA Nemotron-generated explanation; strict citation/contract validation.
- **NextStep**: explicitly invoked bounded administrative verification *proposals*, validated by a deterministic critic. No proposed query execution.
- **Human review**: fictional local JSONL note, not authenticated approval or source update.
- **Meterless**: genuine upstream World Model persistence and read-only archived event index, separately from server-observed activity.

`apps/product` remains the reliable Python-served fallback. `apps/tbcare-next` is an optional local Next.js workbench; **it must be present in the branch for a clone to run it**. No credentials or untracked `outputs/` data belong in Git.

## One-time installation

Clone this branch, rather than main, until the integration candidate is approved:

```bash
git clone --branch integrate/tbcareos-product-g-candidate https://github.com/Z-bros/open-agent-id-health.git
cd open-agent-id-health
python3 -m pip install -e .
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
```

For live source/model mode, have a working locally configured **official Zetaris query helper**, the fabricated five-table `TBCARE_OS` namespace, and a valid NVIDIA key **in the backend process environment**. Never place the key in `NEXT_PUBLIC_*`.

Start backend, from repository root, in its own WSL terminal:

```bash
PYTHONPATH=src:. python3 -m apps.product \
  --helper "$HOME/zetaris-getting-started/scripts/query_zetaris.py" \
  --namespace TBCARE_OS \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --review-dir outputs/reviews \
  --activity-dir outputs/activities \
  --meterless-reference "$HOME/Meterless/engines/world-model/reference" \
  --meterless-state-dir outputs/meterless \
  --port 8765
```

Run frontend (if `apps/tbcare-next/package.json` is tracked on this branch), in a **different** terminal:

```bash
cd apps/tbcare-next
npm ci
printf 'NEXT_PUBLIC_TBCARE_MODE=local\nTBCARE_ENABLE_LOCAL_PROXY=1\n' > .env.local
npm run typecheck
npm run build
npm run dev -- --port 3001
```

- Python fallback: http://127.0.0.1:8765
- Next.js optional frontend: http://127.0.0.1:3001
- `curl -fsS http://127.0.0.1:8765/api/cases`
- `curl -fsS http://127.0.0.1:3001/api/backend/cases`
- `curl -fsS http://127.0.0.1:3001/api/backend/cases/CASE-TB-018/evidence`

Browser should show that it is connected. A successful `/api/cases` response proves the API bridge, not actual model inference; inspect a case and explicitly click both agents for that.

**Offline Python fallback:** `PYTHONPATH=src:. python3 -m apps.product --fixture tests/fixtures/tb_case_018_bundle.json --port 8765`. This is one-case fixture mode; live model buttons still require NVIDIA. The Next.js frontend's own standalone demo mode uses simulated results and must be marked as such.

## Demonstrated test coverage (not universal reliability)

- Participant-verified E09: 36/36 fabricated cases source/contract-integrity evaluation; 163 retrieved source observations; 21 deterministic findings. This did not measure clinical accuracy or holdout-ground-truth precision/recall.
- E10 six-case hosted-model sample: 8/10 validated model outputs; rejection is real and must remain visible.
- Participant browser observation on CASE-TB-006: independently invoked accepted CaseLens and NextStep, with server activity showing provider wait, validation, technical acceptance and awaiting human review.
- Separate participant-run Meterless archival of saved validated CASE-TB-006 artifacts: archive contained 18 events, and replay preserved the same 18 events with 0 duplicate processed observations. **Not automatic on browser agent requests.**
- GitHub CI: offline synthetic Python tests and real upstream Meterless fixture integration passed on the previous integration head. Run current checks after importing the Next.js frontend.

## Explicit limitations

- No patient contact, diagnosis, official system write-back, clinical clearance or authentic reviewer authentication.
- Missing query rows do not prove missed care.
- Technical agent acceptance does not mean an administrative case is resolved.
- Meterless event times represent synthetic source data snapshots, not the wall-clock model-run time.
- Human review note, app activity JSONL and Meterless World Model events are separate ledgers; there is no complete shared request-to-archive trace.
- No automatic Meterless archival from UI and no after-tab-close notifications.
- **Do not publicly deploy the local proxy**: it is designed only for a trusted localhost demo. A publicly visible GitHub repository is different from exposing the localhost service.

## Submission preparation

Make sure `apps/tbcare-next` actually exists in the pushed branch before advertising the Next.js UI as reproducible. Keep locally generated `outputs/`, local `.env.local`, dependencies and synthetic oracle files out of the push. Record a short case 001/009/018 walkthrough, screenshot UI, document accepted and rejected model examples, verify no secrets in Git history, then submit ahead of the stated deadline of 28 October 2026 06:45 WIB.
