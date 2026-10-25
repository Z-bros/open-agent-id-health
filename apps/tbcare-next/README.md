# TBCare optional Next.js frontend v0.3

See [DESIGN_IMPLEMENTATION.md](DESIGN_IMPLEMENTATION.md) for the current design changes, startup instructions, validation and limitations.

> **TBCare integration (23 Oct 2026):** This package is the adapted optional Next.js user interface based on the supplied agentic starter. It does NOT replace the audited Python localhost backend or prove live national-health-system connectivity. The Python frontend remains a reliable fallback. This adapted version uses an independent restrained teal workbench palette, visible technical-review caution statuses, a corrected offline-fixture import, stronger localhost origin enforcement, and a read-only view of the real Phase G application-activity feed in local mode. See `INTEGRATION_GUIDE.md` for the preferred workflow.

# TBCare — Integrated Product Design Frontend

An editable, runnable **UI starter**, not an integrated production system, based on `TB-CareOS_Product_Team_Integration_Handoff(1).md` (23 Oct 2026) and its reference branch `feat/product-phase-f-caselens-schema-prompt` in [`Z-bros/open-agent-id-health`](https://github.com/Z-bros/open-agent-id-health).

**What this is:** a clean white/blue evidence-first administrative investigation interface with **English + Bahasa Indonesia** toggle, responsive layouts, case explorer, the four-stage investigation journey, source provenance, independent CaseLens/NextStep panels, local-review form, activity page, and read-only World Model audit states.

## Agentic UX enhancements (v0 iteration)

The new `app/components/AgentActivity.tsx` implements three connected interaction systems:

1. **Intent & transparent processing states.** A visible four-stage intent strip (**Inspect → Explain → Propose → Human review**) explains which operations are read-only and which require explicit reviewer action. The CaseLens and NextStep panels contain a three-step request-state timeline (request initiated → awaiting backend response → accepted/rejected). It deliberately does **not** claim visibility into private model thoughts or nonexistent token streams. `CASE-TB-001` shows a clearly labelled no-model path.
2. **Human-in-the-loop checkpoints.** A reviewer must explicitly acknowledge inspection of cited source records and confirm that proposed verification steps remain unexecuted, in addition to the existing review-form confirmation, before the local note button is enabled. This gates only the existing local note—not agent execution, external approval, or staff outreach. Changing cases resets confirmations.
3. **Asynchronous in-app notifications.** A bell opens a 30-item **session-only** activity center with unread counters, read/clear actions and toast feedback. Notices are emitted on real client-observed source/agent/review/audit outcomes including failures, stale evidence, and accepted/rejected results. Optional **browser notifications** require a click to grant permission and fire only when an already-requested call completes while the tab is hidden. This is not a backend job queue, push notification service, polling workflow, or durable monitoring. Navigating to another case stops tracking its older request in the UI; this does not guarantee cancellation at the Python backend.

The new UI strings are localized into both English and Bahasa Indonesia in `lib/i18n.ts`, and they are styled consistently with the existing medical blue/white design tokens. These additions preserve the original localhost proxy and model safety boundaries.

Run `npm run test:agentic` to check the component wiring and important safety cues. A full browser build still requires `npm install`.

## Start

```bash
npm install
npm run dev
```

Open **http://127.0.0.1:3000**. `npm run typecheck` and `npm run build` are recommended. Use Node 20 or newer.

By default it runs **demo mode** with three explicit, hand-authored synthetic UI fixtures: `CASE-TB-001` (no deterministic finding), `CASE-TB-009` (current query did not return a lab-result record; CaseLens mock rejection), and `CASE-TB-018` (subject-reference mismatch; simulated accepted responses). The case inventory displays 36 allowlisted IDs, but only those three have bundled offline evidence; other IDs are *not checked*, not secretly fetched or inferred. Agent responses in demo mode are visibly **simulated**, do not call NVIDIA, and do not claim validation by the actual server. Demo review notes exist in browser memory only (lost on refresh). **No Meterless events are invented.** Design-reference PNGs are not tracked in this repository; they are not needed to run the frontend.

## Screens and interactions

- **Case Explorer:** search, filter, select, open cases; counts reflect inspected cases in the **current browser session** only. Opening a case loads evidence; it does **not** invoke either agent.
- **Investigation:** evidence source coverage, table with business ID vs source-row ID vs subject reference, CareFlow findings with citation links, separately triggered CaseLens and NextStep, independent accepted/rejected states, stale-snapshot UX, bounded human review, audit read-only states.
- **Review Activity:** local note preview and note history; never marks findings resolved or delivered.
- **Audit History / Settings:** audit entry point, language choice, data-mode disclosure.

## Optional integration with the *existing* Python localhost API

This is NOT enabled by default. Copy `.env.example` to `.env.local`, uncomment/set:

```env
NEXT_PUBLIC_TBCARE_MODE=local
TBCARE_ENABLE_LOCAL_PROXY=1
```

Run the working Python TB-CareOS server on the **same trusted machine** at `http://127.0.0.1:8765`, using its documented external Zetaris, NVIDIA, and Meterless prerequisites. Restart Next.js. Visit `http://127.0.0.1:3000` on that same machine.

The optional `app/api/backend/[...parts]/route.ts` adapter makes a **restricted localhost-to-localhost** same-origin API bridge for these existing routes only:

| UI operation | Existing Python route |
|---|---|
| List synthetic cases | `GET /api/cases` |
| Read evidence | `GET /api/cases/{id}/evidence` |
| Generate CaseLens, explicitly | `POST /api/cases/{id}/explain` with `X-TBCareOS-Evidence-SHA256` |
| Generate NextStep, explicitly | `POST /api/cases/{id}/plan` with same digest |
| Read local notes | `GET /api/cases/{id}/reviews` |
| Save explicit local review | `POST /api/cases/{id}/reviews` with backend-required review intent, matching finding/category/citations, UUIDv4, and digest |
| Activity index | `GET /api/review-activity` |
| Read previously persisted event metadata | `GET /api/cases/{id}/audit` |

This code **never** makes direct browser SQL calls, talks to NVIDIA from the browser, runs proposed source checks, writes source data, or ingests Meterless events. Agent responses are rendered only after the existing Python backend succeeds. HTTP 409 marks evidence stale; rejected model responses are displayed as rejected. CaseLens failure does not prevent separate NextStep success. Reviewer notes remain local, non-authoritative JSONL writes in the original backend; no SITB or SATUSEHAT integrations exist.

### Security and deployment warning

**Do not deploy the local API bridge publicly**, even with loopback binding. It is gated on explicit environment flags and loopback host and is *only intended for localhost development*. The original Python server enforces loopback Host/Origin checks and is not safe as a public API. A real deployment requires authenticated reviewers, authorization, CSRF prevention, secure proxy architecture, privacy review, secrets management, audit/logging, and a separate deployment/security design. A deployed v0 preview should stay in demo fixture mode.

The language selector translates the interface. It does **not** machine-translate source evidence or accepted server AI reports; those are displayed unchanged to protect citation meaning. Add validated backend localization if needed.

## Files

- `app/page.tsx`: screens, demo actions, local API actions, independent agent/review states
- `app/globals.css`: hospital UI theme and responsive styling
- `lib/i18n.ts`: English / Indonesian interface dictionary
- `lib/demo.ts`: clearly labelled synthetic **UI** fixtures and sample agent-state scenarios
- `lib/api.ts`: typed client for existing backend endpoints
- `app/api/backend/[...parts]/route.ts`: loopback-only, allowlisted Next server adapter
- Optional design-reference PNGs are excluded from the tracked application; they are not runtime dependencies.

## Import to v0

Upload this folder's ZIP or push it to GitHub and import as a project to v0. Alternatively, upload the three reference images and paste the instructions below. Ask v0 to *modify the code* rather than reconstruct screenshots as background images.

### v0 prompt

> Use the attached TB-CareOS Next.js starter as the source code and improve the visual hierarchy to match the three `public/reference/` screenshots. Keep the clean hospital palette: white, subtle sky-blue, refined navy, restrained semantic status colors. Preserve the English/Indonesian toggle and responsive layout. The product is an administrative evidence review workspace for **fabricated** TB-program records, not a diagnosis or treatment app. Preserve all interactive screens (Case Explorer, Investigations, Review Activity, Audit History). Preserve exact source types, row provenance IDs, and independent CaseLens/NextStep accepted/rejected states. Do not invoke models on case selection; keep both explicit buttons. Do not silently replace rejected AI output. Keep NextStep plans labelled PROPOSED / NOT EXECUTED. Keep local reviewer notes separate from real read-only Meterless events, and never fabricate audit records. Preserve the disabled-by-default loopback API boundary; v0 cloud previews must remain in fixture mode. Do not add direct NVIDIA/browser SQL integrations. Optimize the case → discrepancy → cited evidence → accepted/rejected agents → local human review journey for a 2-minute demonstration.

## Reference integrity

The handoff describes the *existing local Python/JS app*, **not** a verified Next.js migration. The Next.js starter is a separate design/frontend layer. No claim is made that backend tests or real Zetaris/NVIDIA/Meterless integration were verified through this starter. Fixture content and illustrative record dates are not evidence of actual source retrieval; the original source-of-truth backend remains in the linked GitHub branch.


## v0 follow-up prompt

See [`V0_AGENTIC_UX_PROMPT.md`](V0_AGENTIC_UX_PROMPT.md) for a copy-paste prompt that asks v0 to refine these exact components and preserve the observable-state and background-notification limitations.
