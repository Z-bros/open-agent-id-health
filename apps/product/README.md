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
