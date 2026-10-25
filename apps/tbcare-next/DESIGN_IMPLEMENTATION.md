# TBCare — institutional health-record review interface (v0.3)

This is an **optional Next.js frontend**, updated against the user's healthcare UI/UX implementation brief. The user-facing name is **TBCare**. Legacy `TBCARE_OS` identifiers stay unchanged only in backend protocol fields. This is *not* an official Kemenkes/SATUSEHAT/SITB product and does not access real patients.

## What changed from the previous adapted frontend

- **Bahasa Indonesia as default**, while English remains available in the header. Switching language retains the case, current screen, filters and evidence. Raw model text and record IDs remain untranslated.
- **Professional, table-first layout**: cooler neutral background, deep-teal-blue navigation, one compact stats strip, readable table headers and tighter source/result panels. No gradient, artificial clinical metrics or consumer-wellness imagery.
- **The case table selects a case** via a real keyboard-accessible case-ID button. The preview panel reflects that selection; the separate *Investigate* button retrieves the evidence only when explicitly invoked.
- **Correct offline inventory behavior**: all 36 synthetic case IDs remain in inventory, but only 001, 009 and 018 have bundled standalone fixture evidence. Other offline actions are disabled rather than presenting a fake source query or fake success. Local API mode enables valid backend IDs when connected.
- **Source check rows** clearly display each of the five tables, its latest reported query attempt, and the actual read status. `not_found` becomes *No rows returned* / *Tidak ditemukan dalam hasil kueri*, never an assertion of missing care.
- **Expandable source evidence rows** expose only retrieved business ID, provenance/row ID, subject reference, and the bounded `details` metadata of that source record. Citations open the corresponding row; all untrusted data are rendered as React text, not HTML.
- **Honest state labels**: partially unavailable source access is amber, stale/rejected operations are red, and a technically accepted model output is amber **review still required**. Review notes do not mean approval; plan checks remain **proposed, not executed**.
- **Backend connection status** shows demo / checking / connected / unavailable, with a retry action. A failed local backend never triggers a substituted demo result.
- **Accessibility**: labeled search, explicit native buttons, `aria-pressed` selected-case state, `aria-expanded` source details, English/Indonesian `html[lang]`, keyboard `:focus-visible` rings and meaningful data table captions. Eight semantic foreground/background color pairs are checked against WCAG 2.1 AA (4.5:1).
- **Next.js workspace warning mitigation**: `next.config.mjs` defines `outputFileTracingRoot: process.cwd()` to keep the optional frontend scoped to its own directory when the parent repo has another package-lock.

## Source/AI safety and supported architecture

- **Python backend remains authoritative** on `http://127.0.0.1:8765`.
- Connected Next.js frontend uses **only** its fixed-path localhost Next API bridge to the existing Python API. Do not expose the proxy publicly.
- Model requests are explicit and include the current `X-TBCareOS-Evidence-SHA256` snapshot digest. No raw SQL, clinical action, source mutation or patient outreach occurs.
- Demo mode responses are **simulated**, and demo mode audit view has **no invented Meterless events**.
- Server Phase G activity, local reviewer notes and persisted Meterless audit are distinct. No workflow is claimed to have verified an official case resolution.
- Clinical performance, SITB/SATUSEHAT interoperability, fully authenticated reviewer identity, integrated agent-to-Meterless write per click, and unified verified source-to-decision trace are **not implemented** by these frontend design changes.

## Validation performed

Validated directly against bundled source:

```bash
npm run test:static
npm run test:agentic
npm run test:integration
npm run test:brief
```

All four commands passed. TypeScript/TSX source was also parsed with the TypeScript transpiler (syntax passed). The semantic AA color-token pairs meet the 4.5:1 normal-text rule.

**Not verified here**: full dependency resolution, `npm run typecheck`, `npm run build`, a rendered-browser accessibility audit, or live browser E2E against Zetaris/NVIDIA/Meterless. `npm install` timed out in the package-building environment; the user must run the build locally.

## Launch (demo or localhost Python API)

Extract the package from the **repository root**, after backing up local edits:

```bash
# In your TBCare repository root, before replacing the previous optional UI:
[ -d apps/tbcare-next ] && cp -a apps/tbcare-next "apps/tbcare-next.backup.$(date +%Y%m%d%H%M%S)"
unzip -o TBCare_Healthcare_UI_v0_3.zip
cd apps/tbcare-next
npm install
npm run test:brief
npm run typecheck
npm run build
npm run dev -- --port 3001
```

The package is a complete updated `apps/tbcare-next` source folder; it excludes `node_modules`, `.next`, `package-lock.json`, local secrets and old incremental TS build artifacts. Download/copy the ZIP into the repo root before running unzip. Keeping `node_modules` from a previous installation is fine after `npm install` reconciles the package.

**Simulated offline mode** (default): no `.env.local` needed. Three supported interactive fixtures: CASE-TB-001, CASE-TB-009, CASE-TB-018.

**Connected local mode:** keep the original Python TBCare server running on `127.0.0.1:8765` with its Zetaris helper and `NVIDIA_API_KEY` environment. Set *in Next.js's `apps/tbcare-next/.env.local`*:

```env
NEXT_PUBLIC_TBCARE_MODE=local
TBCARE_ENABLE_LOCAL_PROXY=1
```

Restart Next.js, open `http://127.0.0.1:3001`, and verify the header actually says **API lokal terhubung** before running agent requests. The Python server credentials must never be added to Next.js.

## Browser acceptance checklist

1. Open case inventory, search for 018 and select its case-ID button (preview updates; no source call yet). Click *Investigate* to retrieve.
2. Expand source evidence IDs `CASE-TB-018` and `RES-TB-018`, verify subject mismatch and provenance. Click a citation to expand/highlight the exact retrieved row.
3. Switch ID→EN and back; no case should be reset or requered solely by translation.
4. In demo mode check 001 no rule finding, 009 unreturned result, 018 subject mismatch; unsupported other fixtures must have disabled entry actions.
5. In connected mode verify live source query states, explicit agent button responses and failure semantics; no accepted result should imply case resolution. Check a rejected explanation and deliberate retry only.
6. Verify source event time is distinguishable from local note time and Meterless event time. Inspect actual history or empty/unavailable audit response; no forged events.
7. Keyboard-only path: Tab, Enter/Space, case-selection button, source-detail toggle, form. Check focus visible at desktop and narrow viewport.
8. Verify `npm run build` and host 3001, including fresh clone / `.env.local` as appropriate.

This package remains an **optional local preview until committed and accepted**. It does not alter PR #23 or the Python product by itself.
