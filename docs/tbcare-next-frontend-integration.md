# TBCare Next.js interface — repository integration

**Updated 25 Oct 2026.** The optional Next.js 15 / React 19 frontend **is now checked into this integration branch** at `apps/tbcare-next/`. It is an alternative presentation layer for the existing Python localhost backend—not an API rewrite, automatic deployment, or replacement of the dependency-light Python UI.

## Mode and runtime

- Default: `NEXT_PUBLIC_TBCARE_MODE=demo`. The UI explicitly labels its three hand-authored synthetic fixtures and simulated agent states. Other case IDs are listed as **Not checked**. No actual NVIDIA, Zetaris or Meterless operations occur in demo mode.
- Connected: start `python3 -m apps.product` with `--helper ... --namespace TBCARE_OS` and `--port 8765`. In `apps/tbcare-next/.env.local`, set `NEXT_PUBLIC_TBCARE_MODE=local` and `TBCARE_ENABLE_LOCAL_PROXY=1`, then restart `npm run dev -- --port 3001`. The allowlisted Next.js server bridge calls only the existing local Python API.
- **Do not deploy the connected proxy on the internet.** The Python server is loopback-only, reviewer labels are fictional, and there is no production-grade identity/permissions/CSRF/deployment boundary. For an online static preview use labeled demo mode only.
- Never put `NVIDIA_API_KEY` in `.env.local` or a `NEXT_PUBLIC_*` variable. A new WSL terminal may need the key loaded privately to perform CLI agent calls.

## Validate in a clean checkout

```bash
python3 -m pip install -e .
python3 -m unittest discover -s tests -v
cd apps/tbcare-next
npm install
npm run test:static
npm run test:agentic
npm run test:integration
npm run test:brief
npm run typecheck
npm run build
npm run dev -- --port 3001
```

The four frontend static suites have been run successfully on the v0.3.1 source. Full Next.js typecheck/build will be verified by the new GitHub Actions workflow, and a **fresh WSL clean-clone with locally running sponsors** remains a manual sign-off item.

## Verified sponsor flows vs remaining gaps

- Read-only synthetic source retrieval, 36-case integrity, and independent hosted CaseLens/NextStep model calls have been participant-verified in the local Python product. Their validation *can fail* and the UI must show rejection.
- User verified CASE-TB-006 through the Next.js-to-Python bridge, including CaseLens and NextStep server-observed `waiting_for_model`, `validating`, `accepted`, and `awaiting_human_review` events. These are local observed milestones, not private model reasoning.
- On 25 Oct the user separately ingested the saved validated CASE-TB-006 synthetic source/explanation/plan artifacts via `apps.careflow.tb_meterless`. Meterless returned 18 persisted events and the participant's replay check confirmed **zero duplicated canonical events** and all three artifact types.
- **Not implemented:** automatic Meterless archival when CaseLens or NextStep is clicked in Next.js, or a common persisted execution trace correlating each model request with its Meterless event IDs and reviewer notes.
- Meterless event timestamps reflect synthetic source snapshots, NOT October model-call times. The `/audit` endpoint never ingests on read. Review notes, local application activity, and World Model history remain separate.

For detailed UI behaviors, commands and safety limits see [frontend README](../apps/tbcare-next/README.md), [Python product runbook](../apps/product/README.md), [E08 archival](../shared/meterless/E08-AUDIT.md), and [Phase G event contract](phase-g-activity-contract.md).

## Acceptance gate before final merge/submission

1. Pass both original backend workflows and the Next.js CI job.
2. Inspect connected `CASE-TB-001`, `009`, `018` (and optionally verified `006`) in the browser. Verify raw business/source-row IDs and `not_found` uncertainty.
3. Exercise at least one technical model acceptance and one fail-closed rejection. Never silently substitute demo output.
4. Confirm local-only review note and read-only historical Meterless access retain truthful timestamps/status boundaries.
5. Review the public repository for credentials, generated local reports, original private branches/history and unintended files; visibility is a separate repository-admin operation.
6. Merge PR #23 only after explicit final review/approval; branch updates do not imply merge.
