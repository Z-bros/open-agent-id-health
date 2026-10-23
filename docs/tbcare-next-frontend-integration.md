# TBCare — optional Next.js frontend integration

**Design handoff:** 23 October 2026, based on the user-supplied
\`tb-careos-agentic-starter(2).zip\`.

The starter is a separate Next.js 15 / React 19 application with:
- Case Explorer table and selected-case preview;
- source-provenance and discrepancy investigation, two independently invoked agents;
- localized English/Bahasa Indonesia interface controls;
- human-review acknowledgements, demo session notices, and separate audit surface.

## Integration decision

**Keep the tested Python server and its existing web frontend intact.**
Adapt the supplied Next app as an **optional frontend at
\`apps/tbcare-next\`**, displayed at \`127.0.0.1:3000\`.
The frontend uses a strictly allowlisted Next API bridge to the original
localhost Python API at \`127.0.0.1:8765\`, *only* when explicitly
configured in local mode. The original Python product stays available on
port 8765. This prevents an unverified frontend replacement immediately
before hackathon submission.

**Source delivery:** The adapted Next source is distributed as the
\`TBCare_Integrated_Next_Frontend.zip\` conversation artifact and is
**not included in this GitHub commit yet**. Unzip the artifact at the
repository root to create \`apps/tbcare-next\`. Do not claim this optional
frontend is deployed or merged into the repo until the source is actually
imported, tested and reviewed.

## How to test it

Frontend-only simulated mode (no Python/model calls):

\`\`\`bash
cd apps/tbcare-next
npm install
npm run test:static
npm run test:agentic
npm run test:integration
npm run typecheck
npm run build
npm run dev
\`\`\`

Visit \`http://127.0.0.1:3000\`. Only the synthetic 001, 009, 018
fixture bundles support offline source views, and their AI outputs are
explicitly simulated.

For connected *localhost only* mode, start the existing real Python
server with the trusted Zetaris, NVIDIA and Meterless environment as in
\`apps/product/README.md\`, then configure
\`apps/tbcare-next/.env.local\`:

\`\`\`env
NEXT_PUBLIC_TBCARE_MODE=local
TBCARE_ENABLE_LOCAL_PROXY=1
\`\`\`

Restart Next dev. All database/model secrets stay exclusively with the
Python backend, **never in browser environment variables**.

The adjusted optional UI includes:
- TBCare branding and muted independent teal health-administration palette;
- table-first case navigator from the uploaded design;
- English/Indonesian labels without translation of raw source/model data;
- technical acceptance shown as *validated, human review required*;
- NextStep proposals *not executed*, no silent substitution for a rejected model;
- 12–280-character note limit matching the original Python review contract;
- actual read-only Phase G \`GET /api/cases/{id}/activity\` history when
  connected; separate from session-only browser notices and Meterless;
- same-origin POST guard and only fixed synthetic API routes.

**No official SITB/SATUSEHAT integration, reviewer authentication,
patient contact, autonomous verification, background worker or closed-tab
push exists.**

## Acceptance remaining

The provided adapted bundle passed its three Node-based static/agentic/
integration verification scripts, but **npm/Next dependencies were absent
in the artifact-building environment**. A completed \`npm run typecheck\`,
\`npm run build\`, live hosted-model and browser-level acceptance tests
are still needed. Do not treat reference PNGs in the starter as proof
of the implemented UI or backend working.

For the exact setup and limitations see the \`INTEGRATION_GUIDE.md\`
included in the adapted ZIP.
