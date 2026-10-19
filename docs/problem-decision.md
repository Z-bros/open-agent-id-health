# Indonesia healthcare problem decision gate

**Target decision:** Oct 20. **Hard freeze:** Oct 21.

| Candidate | Primary user | Exact failure evidence | Test data | Status |
|---|---|---|---|---|
| Referral reconciliation | Puskesmas referral coordinator | Needs direct published evidence | Synthetic records + SATUSEHAT specs | Unselected |
| Diagnostic result follow-up | Radiology coordinator | Needs Indonesian operational evidence | Synthetic order/report logs | Unselected |
| TB care follow-up | Puskesmas TB coordinator | Needs evidence separating disease burden from workflow failure | WHO aggregate + synthetic logs | Unselected |

## Definition of ready
- [ ] One worker and one bounded workflow failure identified
- [ ] One official population-scale source plus one direct process/mechanism source
- [ ] One agent task with objective inputs and human-approved output
- [ ] Three golden test scenarios
- [ ] Sponsor data and inference integrations understood

Do not interpret general disease burden or workforce scarcity as proof of a specific administrative delay.
