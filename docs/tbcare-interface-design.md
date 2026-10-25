# TBCare — interface refresh / public-health visual language

**Date:** 23 October 2026  
**Branch:** \`integrate/tbcareos-product-g-candidate\` (draft PR #23)  
**Scope:** visual presentation only, no changed case-reconciliation rules, agents, credentials, evidence, review dispositions, notifications, or external permissions.

## Design intent

Move the localhost browser application away from the generic "AI dashboard"
look toward a **calm administrative casework tool** for Indonesian TB
programme teams. The page should answer, in this order:

1. Which case am I looking at?
2. What did the retrieved records actually establish?
3. Which administrative discrepancy requires a person's attention?
4. Which explanation/verification suggestions are available (and which are **only proposals**)?
5. What has been recorded in local human-review notes and which audit events are available?

A user should not mistake generated/validated explanation for an officially
resolved case, a missing query result for missed healthcare, or fictional
local review activity for real clinical approval.

## Color direction, not an institutional identity

Kemenkes' public logo philosophy references turquoise and bright green as
markers of trust, openness and public health. TBCare references this **broad
color family** but uses an independent typographic 'T' mark, a muted palette,
original layout, and no Kemenkes emblem or institutional co-branding.
**TBCare is not represented as endorsed, developed or hosted by Kemenkes.**
Reference: https://kemkes.go.id/id/filosofi-logo/

| Token / usage | Independent TBCare value |
|---|---|
| Primary action / teal | \`#087875\` |
| Brand text / deep marine | \`#154B47\` |
| Primary text / dark ink | \`#213C3E\` |
| Supporting text / slate | \`#64797A\` |
| Workspace background | \`#F7F9F7\` |
| Subtle lines | \`#DCE7E3\` |
| Pending verification | amber, not clinical severity |
| Rejected result / stale evidence | restrained red |
| Source-read / neutral non-exception | muted green / neutral, not case clearance |

Brand must **not** visually imitate the Ministry's official mark. The
previous angular star/burst has been replaced by an original plain 'T'
wordmark. There are no external images, remote font downloads, third-party
style dependencies or provider badges resembling accreditation.

## Structural differences

- **Light case navigator** instead of a high-contrast dark SaaS sidebar.
  Active case uses a pale teal row highlight. Source-status labels remain
  distinct from verified review outcomes.
- **Editorial workspace header** with the current case as the largest
  readable line. Source mode explicitly says read-only demo; no fake
  "online/clinical service is live" indicator.
- **Slim synthetic-use notice** replaces a decorative hero callout.
- **Compact example-case launcher** instead of three prominent decorative
  tiles competing with the actual investigation.
- **Four-step review path** with amber human-attention checkpoint when
  an accepted AI result still leaves a discrepancy open.
- **One summary strip** instead of four large floating KPI tiles. Counts
  are descriptive observations, not outcome/KPI claims.
- **Evidence-first two-column layout** (findings dominate; source checks
  secondary); full-width traceable evidence timeline remains available.
- **Plain-language agent panels**: explain the evidence and suggest
  verification steps. CaseLens and NextStep remain visible technical labels,
  but are secondary to the job-to-be-done.
- **Server-observed activity list beside agent work**, rather than another
  huge high-priority box above source evidence. No simulated reasoning.
- **Restrained review and audit details** with citation, guardrails and
  real historical distinctions preserved.

## Implementation

- Existing \`apps/product/web/style.css\` remains intact for compatibility;
  new \`apps/product/web/theme.css\` is an explicit, last-loaded override
  with accessible focus rings, no external assets and responsive views.
- The Python localhost static asset map now serves \`/theme.css\`.
- Existing \`apps/product/web/app.js\` behavior and all API paths remain
  unchanged.
- The activity panel was moved **within case content**, immediately
  after the existing agent panel. Its ID and all JavaScript event bindings
  are unchanged. It does not trigger additional API calls.
- The user-facing \`TBCare\` branding is independent of internal
  compatibility identifiers such as \`TBCARE_OS\`, \`CASE-TB-*\`, and
  \`X-TBCareOS-*\`.

## Acceptance checks

1. Run \`PYTHONPATH=src:. python3 -m unittest discover -s tests -v\`.
2. Run the local product with your existing Zetaris helper, model key, and
   Meterless directories; open \`http://localhost:8765/\` and hard-refresh.
3. Select synthetic 001, 009, 018: case navigator, source checks,
   findings, citations, timeline and empty/loading/error states must
   continue to work.
4. Click Generate explanation and Generate verification plan. Observe the
   truthful button states and **amber review required**, not a green
   "case resolved" signal.
5. Check the activity feed immediately below the agent panel; verify
   independent local reviewer notes and separate genuine Meterless audit.
6. Review at desktop and mobile-width layouts. Confirm buttons, citations,
   source-status labels, form fields and table scroll are accessible.
7. Take a local browser screenshot. **Visual/browser sign-off is not
   demonstrated by the automated DOM/API tests alone.**

This is a design/system readability improvement, **not** a production-ready
healthcare implementation or authorized national-system integration.


## Enterprise public-health workbench refinement — 23 Oct evening

The current workbench now follows the user-specified accessible health
administration constraints beyond the initial color refresh:

- **No wellness-app patterns:** no hero images, gradients, neon outlines,
  dark default surfaces, decorative 3D elements, or consumer CTA banners.
- **Density:** narrower navigator; abbreviated topbar and scenario selectors;
  record status immediately beside the case identifier; compact source,
  findings, event, agent and review rows rather than oversized KPI cards.
- **Legibility:** prefer local \`Public Sans\` if available, with native humanist
  \`Segoe UI\` fallback; **no remote fonts or external font requests**.
  No copyrighted or government font files are copied into this repository.
  Font family will vary across operating systems until an appropriately
  licensed, self-hosted font is packaged and validated.
- **Status semantics:** a single server-grounded case status can read
  \`Not checked\`, \`Reading source records\`, \`Source read unavailable\`,
  \`Partial source access\`, \`Discrepancy · Review required\`,
  \`Discrepancy · Note recorded\`, \`Evidence outdated · Refresh\`, or
  \`No rule-based flags in checked records\`. Statuses use **solid,
  desaturated** amber, red, information, or neutral backgrounds with
  labels. Human-review note recorded is **never official closure**.
- **Color/contrast:** semantic foreground-background pairs are unit-tested
  against WCAG 2.1 AA 4.5:1 minimum for normal text, including action,
  body, neutral, warning, error and retrieved-source labels. Last-layer
  theme overrides also restore darker secondary text. This does not
  replace a browser-level full-screen computed-style accessibility audit.
- **Keyboard:** all case items remain native buttons; Up/Down/Home/End
  move focus without triggering queries; Enter/Space activates a case.
  The list has visible keyboard instructions and explicit 3-pixel
  \`:focus-visible\` outlines. There is also the existing skip-to-investigation
  link, explicit button busy states and accessible status announcements.
- **Literal administrative language:** no invented blood types, clinical
  diagnoses, electronic medical record availability, live FHIR log entries,
  actual \`Nomor IHS\`, SATUSEHAT integration or successful national
  registry writes. The interface explicitly discloses **SIMULATED DATA —
  NOT FOR CLINICAL USE**. Real response semantics are still bound to the
  existing synthetic source contracts.

### Indonesian localization boundary

The copy is deliberately literal and terminology-focused, but **the
current interactive interface remains English**. An Indonesian
translation needs to cover navigation, status, error messages, form labels
and assistive descriptions consistently—not only decorative headings.
Model-generated reasoning should not be silently translated into a claim
of official Indonesian medical terminology. A full \`id-ID\` locale or
language switch is **future scope**; don't advertise bilingual functionality
in this build.

### Acceptance scope

In addition to prior tests, \`tests/test_product_workbench_ux.py\`
checks semantic WCAG contrast pair ratios, authorized synthetic
status words, case-list keyboard behavior, plain-language copy and
absence of invented clinical/FHIR fields. A local browser screenshot
and keyboard-only workflow test are still required before accepting
the visual redesign for the final submission.
