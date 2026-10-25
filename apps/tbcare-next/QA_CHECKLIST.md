# Manual UI acceptance checklist

Run in demo mode first. Do not treat frontend-only demonstrations as proof of live backend integration.

## Case explorer
- [ ] On initial load, all 36 synthetic IDs say **Not checked**; counters are session-only.
- [ ] Search, filters, selection and Case Explorer navigation work.
- [ ] EN and ID switch the navigation, headings, controls, statuses and forms.
- [ ] Open CASE-TB-001: no CareFlow findings and no clinical completion claim.
- [ ] CASE-TB-009: lab_results query is marked **Not found**, not "missed care".
- [ ] CASE-TB-018: source record `CASE-TB-018` and result `RES-TB-018` have different synthetic subject references.
- [ ] A citation focuses the corresponding record row and distinguishes `record_id`, `source_record_id`, `record_type`.

## Agents
- [ ] Merely opening a case does not invoke CaseLens or NextStep.
- [ ] CASE-TB-009, Generate explanation: **Not accepted** demo result and safe rejection code appear; retry is explicit.
- [ ] CASE-TB-009, Generate plan: independent **Accepted** demo result appears, but the overall case stays under human review.
- [ ] CASE-TB-018, Generate explanation and plan: demo-labelled accepted states; plans say **PROPOSED / NOT EXECUTED**.
- [ ] CASE-TB-001, Generate explanation: no-finding response, not implied real model invocation.

## Local note / Meterless
- [ ] Local note save requires finding and explicit checkbox. Note count does not equal resolved.
- [ ] Demo notes are labelled browser-memory previews and disappear after refresh.
- [ ] Meterless audit in demo shows **no real audit data available** and invents no events.
- [ ] English/Indonesian change does not alter raw source business identifiers.

## Actual API mode (requires working local Python, Zetaris, NVIDIA, Meterless)
- [ ] Set `NEXT_PUBLIC_TBCARE_MODE=local` and `TBCARE_ENABLE_LOCAL_PROXY=1` in `.env.local` and restart Next.
- [ ] `GET /api/cases`, evidence and notes use real local backend responses.
- [ ] Agent requests include exact evidence digest; `409` forces refresh and invalidates old results.
- [ ] Model/provider `422`/`503` show explicit rejection/unavailable, no fabricated fallback.
- [ ] Notes POST includes exact selected finding/citations and user intent; saved data comes from local review history.
- [ ] Meterless shows only truly persisted `events()`/`audit()` values or explicit empty/unavailable state.
- [ ] Do not expose the local proxy on a public deployment.

## Tests

```bash
npm run test:static
npm run typecheck
npm run build
```

The first check needs only Node. The latter two require installed npm dependencies and were not validated in this artifact-generation environment where the npm registry was unreachable.
