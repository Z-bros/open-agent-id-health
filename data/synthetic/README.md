# Fabricated synthetic fixtures

- `records.json`: old small generic deterministic fixture; **preserved** for existing five tests.
- `tb_v1/`: **not included in this restructuring commit**. A separate fully fabricated 36-case ZIP was prepared on 21 Oct and supplied to the participant.

Extract the ZIP's `tb_v1/` folder here and keep all support files (including `manifest.json`, `schema.json`, `verify_dataset.py`, `PREBUILD_DISCLOSURE.md`). Then run:

```bash
python3 data/synthetic/tb_v1/verify_dataset.py
```

Keep `ground_truth_holdout.csv` away from agent input; use it only for post-hoc evaluation. No actual TB patient data or official SITB records.
