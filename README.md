# TBCare — synthetic TB administrative evidence investigation

**Hackathon integration candidate.** TBCare is a localhost-first, **synthetic-data-only** workspace for investigating inconsistent tuberculosis-program *administrative records*. It is not a clinical system, does not access the Indonesian national SITB/SATUSEHAT production systems, and must not be used with real patient data.

The interface follows **Inspect → Explain → Propose → Human Review**. All source reads are read-only; all generated verification checks are **proposals, not executed actions**. Technically validated model outputs do not close a case.

## What actually works

| Layer | Implementation and verification boundary |
| --- | --- |
| Zetaris | Official read-only helper queries five locally registered **fabricated** source tables in `TBCARE_OS`; 36/36 cases passed the E09 source/contract evaluation on 23 Oct 2026. |
| CareFlow | Deterministic administrative discrepancies with retrieved record IDs and explicit source-check statuses. |
| CaseLens | On-demand hosted NVIDIA Nemotron explanations, checked by deterministic citation/structure/safety validators; rejection is shown as rejection. |
| NextStep | On-demand model-selected **allowlisted** read-only verification *proposals*, independently checked by a bounded critic and terminated with manual review + stop. |
| Human review | Local, fictional, append-only note ledger with evidence snapshot checks, no authentication or official approval. |
| Meterless | Genuine upstream World Model persistence and read-only historical event viewer. **Archival is initiated by a separate CLI**, not automatically when the browser calls the agents. |
| Activity | Server-observed processing checkpoints in a separate local ledger; neither Meterless events nor model chain-of-thought. |

**Evidence:** the participant verified the 36-case source integrity run (163 observations, 21 rule-based findings; [E09](docs/e09-verified-evaluation-results.md)). A selected six-case hosted Nemotron evaluation accepted 8 of 10 outputs; two failed closed ([E10](docs/e10-verified-nemotron-results.md)). On 25 Oct, CASE-TB-006 had independently validated browser CaseLens/NextStep runs and a separate manual archival of validated artifacts in Meterless (18 persisted events, replay added zero canonical events). These measurements are synthetic administrative contract tests—not diagnostic accuracy, independent ground-truth precision/recall, or verified patient outcomes.

## Run the product — two frontends, one Python backend

**Prerequisites:** Python 3.10+, Node.js 22 recommended for the optional Next.js frontend, locally configured read-only Zetaris helper, and (only for live agent calls) a valid `NVIDIA_API_KEY` in the **Python process environment**. Upstream Meterless checkout/npm dependencies are required only for archival and the real audit viewer.

Run from the repository root:

```bash
python3 -m pip install -e .
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
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

Open **http://127.0.0.1:8765** for the verified dependency-light Python-served interface.

Optional **Next.js 15 / React 19** interface, now tracked under [`apps/tbcare-next`](apps/tbcare-next/README.md):

```bash
cd apps/tbcare-next
npm install
npm run test:static && npm run test:agentic && npm run test:integration && npm run test:brief
npm run typecheck && npm run build
npm run dev -- --port 3001
```

Next.js starts in *explicit demo mode*: the three UI fixtures are simulated and do not call the backend. To connect Next.js to the **already-running** local Python server, put exactly the following in `apps/tbcare-next/.env.local` and **restart Next.js**:

```env
NEXT_PUBLIC_TBCARE_MODE=local
TBCARE_ENABLE_LOCAL_PROXY=1
```

Check `curl -fsS http://127.0.0.1:3001/api/backend/cases`; a successful inventory response proves only the proxy, not a successful source or model call. Case selection then fetches actual synthetic source evidence; explanation and planning are separately invoked. **Never enable this local proxy on a publicly deployed frontend.** A public demo must stay in clearly labeled fixture mode.

If Zetaris is unavailable, use the original Python fixture-only mode:

```bash
PYTHONPATH=src:. python3 -m apps.product --fixture tests/fixtures/tb_case_018_bundle.json --port 8765
```

This displays one saved fabricated evidence bundle; it does **not** invent live hosted AI responses. More complete runbooks: [Python product](apps/product/README.md), [Next.js integration](docs/tbcare-next-frontend-integration.md), [Meterless E03](docs/e03-meterless-runbook.md), [E08 agent archival](shared/meterless/E08-AUDIT.md), [Phase G](docs/phase-g-activity-contract.md).

## Architecture and guardrails

```text
Next.js localhost UI (optional) --loopback proxy--> Python localhost product API
                                                       |
                                       Zetaris read-only synthetic tables
                                                       |
                                           CareFlow deterministic findings
                                                       |
                              explicit CaseLens and/or NextStep Nemotron calls
                                                       |
                           strict citation / schema / action-bounds validation
                                                       |
                 local review notes             separate observed activity log

Separate CLI: validated saved reports -> real Meterless WorldModel.ingest
Read-only audit UI: previously persisted Meterless event metadata
```

No automatic proposed-query execution, patient contact, diagnosis, treatment recommendation, approved record change, authenticated reviewer workflow, background worker, or official integration exists. `not_found` means **this query returned zero rows**, never proof of missed care. Evidence timestamps, runtime activity timestamps and local review-note timestamps are not interchangeable.

## Source and submission status

- Original Python workbench lives at [`apps/product`](apps/product).
- The optional bilingual case-explorer frontend lives at [`apps/tbcare-next`](apps/tbcare-next); source files are tracked, with no design-reference PNGs or secrets.
- GitHub Actions test Python/offline contracts and genuine Meterless fixture ingestion; Next.js has its own build/typecheck workflow.
- Current changes are staged in **draft PR #23** for review against `main`, **not yet merged**. See [submission readiness](docs/submissions/tbcare-submission-readiness-2026-10-25.md).
- Historical scaffolding and pre-kickoff provenance remain in Git history; see [prebuild disclosure](docs/prebuild-disclosure.md).

**Not production-ready.** The local proxy and review notes have no production authentication, authorization, or patient-data protections. Use entirely fabricated identifiers and keep `.env`, API keys, `outputs/`, and the benchmark ground-truth holdout out of Git.
