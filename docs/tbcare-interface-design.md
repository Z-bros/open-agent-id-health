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
