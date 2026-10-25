# TBCare Phase G — observed agent activity and human attention

**Candidate:** \`integrate/tbcareos-product-g-candidate\` (from Phase F), 23 October 2026.
**Scope:** localhost synthetic administrative investigation, read-only Zetaris,
real hosted Nemotron, separate local review ledger and genuine upstream Meterless.

## Why this layer exists

The user should see what the application **actually did**, whether an
AI output passed independent validation, what is waiting for an explicit
human action, and what requires attention. No model chain-of-thought is
provided, reconstructed, or implied by these statuses.

The activity feed is a **fifth distinct application-level storage surface**,
NOT the upstream Meterless event stream, CareFlow source evidence, a reviewer
decision, or an external notification service.

## Phase G.1 — user-facing button and review semantics

- When a user explicitly clicks either agent button, it immediately displays
  "Sending ... request". The page subsequently reflects **only observed
  server checkpoints** in the same button (source retrieval, model wait, and
  reply validation), with a CSS spinner that honors reduced-motion settings.
  No client timer invents a model's internal work.
- A CaseLens explanation or NextStep plan that passes technical validation
  is **not case clearance**: the result is amber and says "Review required".
  NextStep explicitly says its proposed queries are *not executed*.
- When no discrepancy was flagged, the status is neutral and explicitly
  says source completeness is not certified. Rejected or stale outputs are
  red and retain the existing deliberate retry/refresh workflow.
- The server activity event `accepted` is retained for backward-compatible
  technical event contracts, but its user-visible label distinguishes a
  validated *step* from administrative case resolution.
- TBCare is the product-facing name. The existing `TBCARE_OS`
  SQL namespace, `CASE-TB-*` identifiers and `X-TBCareOS-*`
  API headers remain unchanged for compatibility.

These improvements do not add an asynchronous worker, clinical urgency
classification, official approvals or automated source writes.

## Current functionality (Phase G initial slice)

- The Python localhost server records server-observed milestones in local
  append-only JSONL files (default \`outputs/activities/\`). Each record
  contains only a synthetic case ID, operation, finite state, UTC
  recorded time, per-request UUID and a safe local error code when needed.
- \`GET /api/cases/{case_id}/activity\` returns up to the last 100 validated
  records, counts and an explicit \`background_worker_active:false\` flag.
  It never performs inference, source queries or Meterless ingestion.
- The browser displays up to 16 recent actual milestones and polls the
  read-only API every two seconds **only when its tab is visible**.
  Notifications are in-app and session-local; there is NO worker, email,
  push service, closed-tab delivery, or autonomous scheduled agent.
- Only previously unseen, server-originated, important states generate an
  in-app attention announcement. Users may click **Mark noticed**, which
  changes only the current page's read indicator, **not** persisted
  evidence/reviewer status.
- When a user explicitly triggers a CaseLens or NextStep request with an
  evidence snapshot hash, the server records requested, retrieval, real
  provider-wait boundary, response-validation boundary, then accepted,
  rejected or failed. On accepted output requiring human approval it records
  an **awaiting_human_review** handoff, not approval.
- \`GET .../evidence\` records requested/retrieval/accepted *only after*
  actual server request; it does not imply clinical data completeness.
- A successful local review-note POST records \`review_note_recorded\`
  using the original idempotency UUID; replays do not create a second
  activity note. The distinct \`outputs/reviews\` ledger remains the
  source of the actual note content and audit semantics.
- The existing real Meterless audit viewer is unchanged and remains
  explicitly separate. Opening this activity feed NEVER ingests/replays
  Meterless events.

## Allowed server-observed states

| State | Meaning | Allowed source of truth |
|---|---|---|
| \`requested\` | HTTP handler received explicit read/model request | Server route |
| \`retrieving_evidence\` | Server began bounded source retrieval | ProductService/handler |
| \`waiting_for_model\` | Model client's \`complete()\` was actually called | Client wrapper only |
| \`validating\` | Provider returned text; local validator will run | Model client wrapper |
| \`no_model_needed\` | Validated path completed without invoking provider | ProductService |
| \`accepted\` | Server handler received a fully validated result | Handler success path |
| \`rejected\` | Existing model output validator rejected result | Handler failure path |
| \`failed\` | Provider, source or internal operation failed | Handler failure path |
| \`stale_evidence\` | Re-read source hash differs from client's snapshot | Snapshot validator |
| \`awaiting_human_review\` | Accepted result still requires staff review | Validated result |
| \`review_note_recorded\` | Real local synthetic note was saved | ReviewStore success |

Important: "awaiting human review" is **not** a newly created review
task assigned to an authenticated staff member. It is a required
administrative handoff. "Review note recorded" is **not** clinical clearance,
a source update, or a delivered escalation.

The private details behind Nemotron reasoning are not available and do
not constitute application activity events. Never display fabricated
"thinking through X..." steps.

## Integration paths

\`\`\`text
Browser explicit click
  → Python ThreadingHTTPServer /api/cases/<synthetic_id>/(evidence|explain|plan)
    → ActivityStore: requested
    → Zetaris read-only / CareFlow: retrieving_evidence
    → CaseLens/NextStep (only when explicitly clicked):
         _ObservedModel.complete: waiting_for_model
         NVIDIA reply returned: validating
         existing strict agent validator: accepted | rejected | failed
         optional awaiting_human_review after accepted
    → append-only local ActivityStore case events

Browser while visible
  → GET /api/cases/<synthetic_id>/activity (2s polling)
    → read-only local JSONL → in-app milestone feed/attention counter

Separate unchanged surfaces:
  ReviewStore (local note content/idempotence; NOT official approval)
  Meterless WorldModel (real persisted upstream event index; NOT this feed)
\`\`\`

The server does not automatically call the model during case selection.
The activity GET cannot trigger a model or source read. There is no
SITB/SATUSEHAT write, patient contact, or automatic NextStep execution.

## Data contract

A single event (schematic; UUID/time provided by server, not client):

\`\`\`json
{
  "schema_version": "1.0.0",
  "event_id": "<server UUID>",
  "run_id": "<one request UUID>",
  "case_id": "CASE-TB-018",
  "operation": "caselens",
  "state": "waiting_for_model",
  "occurred_at_utc": "<actual server clock ISO-8601 UTC>",
  "error_code": null
}
\`\`\`

Allowlisted operations: \`careflow\`, \`caselens\`, \`nextstep\`, \`review\`.
No raw model outputs, prompts, source rows, free-form descriptions,
API keys, reviewer identifiers or real-patient information are stored.

The local files use exclusive Linux file locks, 0600 file permissions,
bounded event count/byte length, and corruption detection. The demo is
localhost only, not authenticated production infrastructure.

## WSL manual acceptance

From repository root, after preserving any uncommitted local changes:

\`\`\`bash
git fetch origin
git switch --track origin/integrate/tbcareos-product-g-candidate
PYTHONPATH=src:. python3 -m unittest discover -s tests -v
PYTHONPATH=src:. python3 -m apps.product \
  --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
  --namespace TBCARE_OS \
  --model nvidia/nemotron-3.5-lightning-30b-a3b \
  --review-dir outputs/reviews \
  --activity-dir outputs/activities \
  --meterless-reference "$HOME/Meterless/engines/world-model/reference" \
  --meterless-state-dir outputs/meterless --port 8765
\`\`\`

Open \`http://localhost:8765/\`, hard-refresh, and select CASE-TB-018.
The page should show server-observed CareFlow request/retrieval/accepted
events. Explicitly generate CaseLens; the feed should show
\`waiting_for_model\` only after actual hosted invocation,
\`validating\` only after a provider reply, and \`accepted\`
or \`rejected/failed\` only following real result status.
The in-app alert counter changes only when new genuine events arrive
while the page is open. Test an explicit local reviewer note. Verify
the Meterless event panel still shows separately persisted upstream
events without misleading crossover.

## Future scope — **not yet implemented**

A real asynchronous queue would need durable job state, a restart-safe
worker, bounded scheduling/concurrency, permissioned cancellation/retry,
status after tab closure, and a separately authorized notification
transport (Web Push/email). None of that is part of this slice.

**Release caveat:** The candidate is stacked from the full Phase F head
but targets \`main\` as a consolidated integration candidate. It MUST
be reviewed and cold-start tested. GitHub CI + local participant acceptance
does not justify claiming the main branch has already shipped.
