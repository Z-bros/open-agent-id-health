# TB-CareOS product phase A — interactive local case explorer

**First product surface, built 22 October 2026.** This is a REAL browser
application backed by the existing tested Python agents, not the static
E06 HTML report. Its scope is deliberately limited to a safe product slice:
interactive fabricated case selection, evidence retrieval/timeline, CareFlow
findings with clickable business ID citations and **explicit** NVIDIA Nemotron
CaseLens and NextStep actions. Review decisions and an interactive Meterless
audit browser are still **NOT IMPLEMENTED** and are visibly labeled as such.

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
