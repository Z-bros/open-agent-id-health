# TB-CareOS product phase A — interactive local case explorer

**Interactive product, first built 22 October 2026; Phase B added 23 October.**
This is a real browser application backed by the tested Python agents, not the
static E06 report. Its current features include fabricated case selection,
evidence timeline and citations, opt-in NVIDIA CaseLens/NextStep actions,
**explicit local administrative reviewer notes** and local note history.
The interactive Meterless audit-event browser is **NOT IMPLEMENTED** (Phase C).
Reviewer notes do **not** imply verified reviewer identity, official case
approval, source verification, or an escalation delivered to staff.

The app binds ONLY to 127.0.0.1. It uses Python's standard-library HTTP
server and self-hosted HTML/CSS/JavaScript, with no required Python/Node
package installation. This is a pragmatic local-first demo rather than a
production deployment or the originally proposed full Next.js/FastAPI stack.

## Start with real read-only Zetaris

From project root in your WSL2 terminal:

    git fetch origin
    git switch --track origin/feat/product-phase-a-local-app
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.product \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --port 8765

Keep the terminal running and open http://localhost:8765/ on your
Windows browser. If browser-to-WSL2 loopback forwarding is disabled, open
the URL from your WSL browser or configure local WSL port forwarding.
This app intentionally refuses to bind to a non-loopback interface.

The 36 synthetic IDs are an *inventory of known IDs*, not claims about
per-case source availability. Clicking a case queries five registered
Zetaris synthetic tables through the real official read-only helper.

**Model buttons are opt-in.** Click Generate explanation or Generate
verification plan to call NVIDIA Nemotron using the model ID chosen at
startup and your existing shell NVIDIA_API_KEY. API errors are displayed
as errors. The UI NEVER invents an offline response after a failed call.
Calls fetch the latest evidence again to reduce stale evidence risk; the
generated answer must still be verified against its own source snapshot.

## Zero-network offline product demo

To try the interface without NVIDIA or Zetaris access:

    PYTHONPATH=src:. python3 -m apps.product \
      --fixture tests/fixtures/tb_case_018_bundle.json \
      --port 8765

Only CASE-TB-018 appears in fixture mode. Real CaseLens and NextStep
button clicks still require NVIDIA; no mock answer is generated.

## Troubleshooting agent buttons (CASE-TB-012, or any synthetic case)

Successful CareFlow evidence retrieval does **not** guarantee that NVIDIA
inference will be permitted or that every generated sentence passes the
grounding validator. For example, a lab result status of "not_found" with a
retrieved order ID is legitimate evidence of an *administrative review
question*, not evidence that care was omitted.

When you see a model error, the API now exposes one **sanitized** error_code
and next_step; it does not expose raw provider response bodies or credentials.

- nvidia_key_missing: NVIDIA_API_KEY was not in the **server process
  environment**. Setting it in another WSL terminal does not update a
  running server. Stop the server, load the key privately, and restart.
- nvidia_access_denied: NVIDIA HTTP 401 or 403; inspect model entitlement
  and key locally.
- nvidia_model_unavailable: NVIDIA HTTP 404; inspect the requested model.
- nvidia_timeout, nvidia_rate_limited or nvidia_incomplete_response:
  provider unavailable/limited or did not return a complete valid answer.
- agent_validation_rejected: the model/source output did not pass
  deterministic citation, format or bounded-action checks. Do not bypass
  the checks or invent supporting records.

Confirm only whether the key is loaded; do not echo its value:

    python3 -c 'import os; print("NVIDIA_API_KEY available:", bool(os.getenv("NVIDIA_API_KEY")))'

To load a key in a WSL Bash shell without putting it in command history:

    read -rsp "NVIDIA API key: " NVIDIA_API_KEY
    echo
    export NVIDIA_API_KEY

Then run the same CaseLens CLI separately to get a safe diagnostic:

    PYTHONPATH=src:. python3 -m apps.caselens \
      --case-id CASE-TB-012 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3.5-lightning-30b-a3b

For a clearly labeled **offline NextStep deterministic baseline** when
the provider is unavailable, use the CLI, not the product's model button:

    PYTHONPATH=src:. python3 -m apps.nextstep \
      --case-id CASE-TB-012 \
      --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --offline

Offline output is not represented as a Nemotron answer.

## Product guardrails

- Only synthetic IDs CASE-TB-001 through CASE-TB-036 accepted.
- Only the official read-only SQL connector and 5 fabricated sources.
- The app does not execute NextStep proposed follow-up checks.
- No patient contact, clinical interpretations, approval submissions,
  SQL mutations or record changes. All administrative exceptions require
  human review; a missing source record does not mean missed care.
- The Python server is loopback-only, with same-origin browser API and
  no credential exposure. It is NOT a production security boundary; do
  not port-forward to external networks or use real patient data.
- Static JS renders retrieved text with textContent, not raw innerHTML.
- No live updating case queue: the case list advertises an unverified
  inventory; opened cases show their actual query results.
- Current E08 Meterless audit write is verified from its separate CLI,
  but app buttons are not yet wired to that audit. This is visibly
  marked as a later phase.

## Product acceptance checkpoint

- Judge can open a browser, select a synthetic case, see CareFlow findings,
  click business IDs and inspect source timestamps without CLI commands.
- CaseLens and NextStep can be triggered through explicit UI controls
  with their real backed Python methods, and errors are honest.
- Product tests cover normal fixture mode, 36-case ID inventory truthfulness,
  static assets, API routes, forbidden mutations, cross-origin requests,
  and redaction of model/provider errors.
- Phase B/C: implement explicit review decision log, real Meterless event
  browser, and additional three-case usability validation.

See docs/product-mvp-roadmap.md for the required full product journey.

## Phase B: explicit human administrative review notes (23 Oct 2026)

This branch extends Product A with a **local, append-only review ledger**
at outputs/reviews/ (configurable via --review-dir). Reviewers may choose
only a retrieved CareFlow finding, add a fictional DEMO-* reviewer label,
choose an explicitly limited administrative disposition and enter a short
neutral note. A checkbox confirms that this is **not** a case approval.

Permitted local-only dispositions:
- request_source_verification — propose checking existing evidence
- escalate_admin_review — flag an administrative escalation in the local log
- reviewed_unresolved — document unresolved administrative review

These are **not clinical outcomes, completed source checks, genuine human
authorization, or official registry updates**. There is no login; the
fictional reviewer tag is self-asserted and human identity is not verified.
Do NOT use real names, phone numbers, email addresses or patient details.

### Review demo in WSL2

    git fetch origin
    git switch --track origin/feat/product-phase-b-human-review
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

    PYTHONPATH=src:. python3 -m apps.product \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --review-dir outputs/reviews \
      --port 8765

Open http://localhost:8765/ and choose CASE-TB-018. Scroll to
**Administrative human-review notes**, choose a cited finding, select a
disposition, keep the fictional tag DEMO-REVIEWER, type a neutral note,
check the explicit acknowledgment and click **Record local review note**.
Confirm a new entry appears with a real UTC timestamp and linked evidence
IDs. Reopen the app to confirm that local history persists.

The synthetic-only fixture works without a Zetaris service; submitting
review notes does not require NVIDIA inference:

    PYTHONPATH=src:. python3 -m apps.product \
      --fixture tests/fixtures/tb_case_018_bundle.json \
      --review-dir outputs/reviews \
      --port 8765

If this branch cannot be checked out due to local edits, stash only the
conflicting files first (do not force checkout or discard edits).

### API and safety guarantees

- GET /api/cases/CASE-TB-018/evidence returns the regular evidence bundle
  plus a server-generated evidence_snapshot_sha256. This hash commits to
  the exact synthetic evidence available during the UI read.
- GET /api/cases/CASE-TB-018/reviews reads only already-recorded local notes.
- GET /api/review-activity shows **only cases with saved local notes**, never
  infers whether other cases were reviewed.
- POST /api/cases/CASE-TB-018/reviews requires same-origin browser,
  application/json, an explicit X-TBCareOS-Review-Intent header, bounded
  JSON, selected finding and exact citation IDs, a matching refreshed
  evidence snapshot hash, fictional reviewer label, allowed disposition,
  neutral note, and a UUID v4 retry key.
- A changed evidence snapshot is rejected with HTTP 409 so the reviewer
  must refresh. Reusing the same request ID and exact content returns
  the original event rather than appending a duplicate.
- Local notes are written as case-scoped JSONL with owner-only file
  permissions (Windows mount filesystem permission semantics may differ),
  O_APPEND, fsync, Linux file locking, and corruption detection.
- The server remains bound to 127.0.0.1 and checks the Host header.
  Review submissions also require an Origin matching the server. This
  is a **localhost demo**, not a deployment-ready authentication scheme.
- No Zetaris writes, no patient contact, no NextStep query execution,
  no real identity verification, no auto-approval, and no clinical assertions.
- The local review history is currently **separate from Meterless**.
  Product Phase C must implement the actual Meterless audit-event browser
  and, if desired, an explicit bridge for validated human review notes.

Only synthetic records are permitted, and held-out evaluation labels
must never enter the app or agent prompts.

## Phase C: real Meterless World Model event browser (23 Oct 2026)

The case detail page now includes a **Meterless World Model audit** section.
It reads actual previously persisted local World Model history through the
separately installed upstream reference. Opening this section does not
invoke WorldModel.ingest(), execute a NextStep plan, or invent sample events.

The read-only API is GET /api/cases/{case_id}/audit, backed by the
apps/product/audit_reader.py adapter and the upstream WorldModel events()
and audit() accessors via scripts/meterless-audit-reader.mts. The UI
shows bounded event IDs, event kinds, event times, and actual persistence
counts. Source audit internals may contain arbitrary text, so the browser
receives only sanitized genuine event metadata.

### WSL2 walkthrough

Stop the old server with Ctrl+C and switch to Phase C:

    git fetch origin
    git switch --track origin/feat/product-phase-c-meterless-audit
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Launch, pointing at the existing E08 state (no re-ingest required):

    PYTHONPATH=src:. python3 -m apps.product \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --review-dir outputs/reviews \
      --meterless-reference "$HOME/Meterless/engines/world-model/reference" \
      --meterless-state-dir outputs/meterless \
      --port 8765

Open http://localhost:8765/ and select CASE-TB-018. Scroll down to
**Meterless World Model audit**. A previously ingested case should show
persisted evt_... event IDs and actual event/audit counts. The UI must
not show invented events for cases never ingested. If Meterless is
unavailable, the panel reports this explicitly.

### Honest audit semantics

- Meterless event times derive from fabricated evidence snapshots.
  They are **not** real inference or human-review submission times.
- Local reviewer notes have real UTC submission timestamps, but they
  remain in a separate local JSONL ledger; do not claim they are
  Meterless events.
- WorldModel event kinds such as upsertEntity and relate are genuine
  internal event types, NOT one-to-one feature labels for the three
  AI agents, nor proof a planned source query was executed.
- The panel shows a bounded recent event index, not all internal
  upstream event or audit text.
- Reviewer notes now require at least four words, plus the existing
  safety and length checks. This catches simple placeholder gibberish,
  not every semantically meaningless note.
- This is a localhost synthetic demo, not an authenticated production
  care-management product.


## Phase D — guided investigation UX (23 October 2026)

This iteration makes the existing read-only product workflow easier to follow
for a first-time hackathon judge, without introducing new source integrations
or changing the CaseLens/NextStep model validators.

**New interactive affordances**

- Three *optional* synthetic demonstration shortcuts for CASE-TB-001,
  CASE-TB-009 and CASE-TB-018. Clicking one retrieves actual evidence;
  the scenario label does **not** insert canned results or run AI.
- A four-step journey: (1) inspect source evidence, (2) explicitly request
  agents, (3) record a fictional local administrative note, (4) inspect
  genuine read-only Meterless history.
- The **Continue** button only scrolls/focuses the relevant existing
  section. It does not invoke an agent, save a review, or run a query.
- Source results in the sidebar are displayed only for cases opened in the
  **current browser session**. Unvisited cases stay **Not checked**, even
  if that case had a finding in an earlier test report. Persisted local note
  badges are loaded separately and do not mean a case was approved.
- The journey separates an accepted AI result from a rejected one and
  a genuine Meterless audit from missing/unavailable persisted history.
  NextStep can succeed independently even when CaseLens fails; **both**
  must succeed for a fully validated explanation-and-plan demonstration.
- No-finding cases correctly show when no hosted model call was needed
  rather than falsely claiming a successful hosted inference.
- Keyboard navigation includes a skip link, focusable investigation
  sections, and live status messages; responsive mobile layouts are
  improved. Source text still renders only through textContent.

**Snapshot protection:** The browser sends the server-generated
SHA256 evidence snapshot identifier on each explicit CaseLens/NextStep
request. The server independently re-queries evidence and compares
hashes **before** invoking Nemotron. A mismatch returns HTTP 409
`evidence_snapshot_changed` and asks the participant to
refresh evidence. Existing displayed agent outputs are invalidated and
the old case's session badge is marked stale. This avoids presenting
AI results from a newly queried source beside an outdated evidence
timeline. The review-note POST already has its own evidence hash check.

**Important:** This does not implement user authentication, official
administrative approvals, a human escalation delivery, an integration
between local review notes and Meterless, or model fallback/retry that
silently bypasses validation. No artificial clinical state is inferred.

### Browser acceptance

From the repository root in Ubuntu WSL2:

    git fetch origin
    git switch --track origin/feat/product-phase-d-guided-workspace
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Start the same existing app:

    PYTHONPATH=src:. python3 -m apps.product \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --namespace TBCARE_OS \
      --model nvidia/nemotron-3.5-lightning-30b-a3b \
      --review-dir outputs/reviews \
      --meterless-reference "$HOME/Meterless/engines/world-model/reference" \
      --meterless-state-dir outputs/meterless \
      --port 8765

Open http://localhost:8765/ and hard-refresh the browser.

Suggested check sequence:

1. The three optional scenario cards appear at the top. Select CASE-TB-009
   and verify the case source checks/findings reflect actual Zetaris queries.
2. A previously unvisited case in the sidebar says **Not checked**. After
   selecting it, the sidebar shows the actual observed finding count for
   that session (not a judge-defined ground-truth label).
3. Click a journey stage: it scrolls to the corresponding section and
   does **not** trigger a provider call.
4. Generate CaseLens/NextStep explicitly on CASE-TB-018. Accepted outputs
   are marked accepted. A rejected response displays a safe diagnostic
   and does **not** become a completed step or a substitute explanation.
5. Record a neutral, fictional DEMO-* review note only after explicit
   acknowledgment (optional); confirm it appears in local history.
6. Verify the Meterless event viewer displays only genuine persisted
   event counts or the explicit unavailable/empty state.

Screenshot verification in the participant's actual WSL browser is
pending; automated CI includes Python product API tests, UI DOM contract
checks and JavaScript syntax checking when Node.js is available.
