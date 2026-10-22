# TB-CaseLens — E04 Nemotron explanation module

**Status (22 Oct 2026):** The post-kickoff evidence-grounded module and CLI
are implemented in branch feat/caselens-nemotron-e04. The prebuild version
was an empty --help scaffold. Offline tests with a mocked LLM passed.
**A real NVIDIA Nemotron inference call has NOT yet been demonstrated from
the participant's WSL2 terminal.** Do not present mock outputs as inference.
All data is fabricated TB administrative metadata.

CaseLens accepts evidence_bundle.v1 from CareFlow and emits the existing
explanation_report.v1 contract. Its job is nonclinical explanation, never
autonomous clinical advice, human contact or treatment decisions.

## Model vs deterministic controls

- CareFlow (rules) chooses exact exception category, record ID citations and
  source-check status.
- NVIDIA Nemotron (external inference) drafts a textual reason and one
  human-review question per exception.
- CaseLens (validator) fixes hypothesis labels, source IDs and provisional
  supported/unresolved assessment; invalid model output is rejected.
- Every report requires human approval; no holdout/oracle labels used.
- With zero CareFlow exceptions, CaseLens returns an empty hypotheses report
  WITHOUT making a model call, and preserves source completeness uncertainty.

The validator rejects non-retrieved event and subject citations, invalid
output, omitted required citations and common clinical claims. This is NOT
proof of full factual correctness. Human review remains mandatory.

## Provider details

Official NVIDIA Build HTTPS endpoint:
https://integrate.api.nvidia.com/v1/chat/completions

API documentation:
https://docs.api.nvidia.com/nim/reference/nvidia-nemotron-3-super-120b-a12b-infer

Default model: nvidia/nemotron-3-super-120b-a12b. Override via NEMOTRON_MODEL
or --model if the participant's account permits another Nemotron model.
A personal NVIDIA Build key in the shell variable NVIDIA_API_KEY is required
for nonempty findings and calls may consume quota/credits.

**Meterless World Model is NOT the NVIDIA inference API.** The official
direct NVIDIA route is not proof of an organizer-sponsored Meterless gateway.
Model availability and organizer-approved inference route are separate.

Keep all credentials local and out of GitHub and chat.

## Run in WSL2

From the TB-CareOS repository root:

    git fetch origin
    git switch --track origin/feat/caselens-nemotron-e04
    PYTHONPATH=src:. python3 -m unittest discover -s tests -v

Test existing real E02 input WITHOUT NVIDIA inference:

    PYTHONPATH=src:. python3 -m apps.caselens \
      --case-id CASE-TB-018 --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py --dry-run

Obtain a personal NVIDIA Build key only if authorized. Load without displaying
it or placing it in your shell history:

    read -rsp "NVIDIA API key (hidden): " NVIDIA_API_KEY
    echo
    export NVIDIA_API_KEY

Run genuine NVIDIA inference:

    PYTHONPATH=src:. python3 -m apps.caselens \
      --case-id CASE-TB-018 --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --output outputs/e04_case_tb_018.json

### Authorized Nemotron 3 Ultra fallback (22 Oct 2026)

Participant obtained **HTTP 200** for a minimal hosted NVIDIA chat completion
using `nvidia/nemotron-3-ultra-550b-a55b`, while the default Nemotron 3
Super returned 404 and Nemotron 3.5 Lightning returned 403. This verifies
Ultra endpoint access **only**, not yet a successful end-to-end E04 report.
The adapter explicitly sends `reasoning_effort: none` for Ultra, matching the
minimal probe and conserving its bounded strict-JSON response budget. Ultra is
hosted; no local 550B model download is required.

    PYTHONPATH=src:. python3 -m apps.caselens \
      --case-id CASE-TB-018 --namespace TBCARE_OS \
      --helper ~/zetaris-getting-started/scripts/query_zetaris.py \
      --model nvidia/nemotron-3-ultra-550b-a55b \
      --output outputs/e04_case_tb_018.json

If Ultra returns invalid JSON or incomplete citations, CaseLens fails closed;
retain the error and diagnose model conformance rather than disabling checks.

Or test with a saved **synthetic** E02 bundle (no Zetaris required):

    PYTHONPATH=src:. python3 -m apps.caselens \
      --case-id CASE-TB-018 \
      --bundle tests/fixtures/tb_case_018_bundle.json \
      --output outputs/e04_case_tb_018.json

Only fabricated data may be transmitted to NVIDIA. Neither Zetaris nor
Meterless credentials are sent. The output file is under .gitignored outputs/.

If the model returns malformed or unsupported claims, CaseLens fails closed.
Do not disable the evidence validator or silently substitute a mocked answer.

## Known limitations / pending

- Lexical and citation checks are NOT complete factuality verification.
  Semantic contradictions, cross-case benchmarks, and LLM quality evaluation
  still require further work.
- E04 explanations are NOT yet appended to Meterless history (E03 archives
  only source evidence and CareFlow findings).
- E02 delayed visibility/source-check retry simulation remains pending.
- No actual patient data, clinical outcomes, human outreach or source writes.
- Live Nemotron inference and account permissions require participant testing.
