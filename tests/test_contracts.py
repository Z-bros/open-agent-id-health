"""Prebuild structural JSON contract checks; not end-to-end sponsor tests."""
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "shared" / "contracts"
NAMES = ("evidence_bundle", "explanation_report", "verification_plan")

class ContractShapeTests(unittest.TestCase):
    def test_contract_examples_contain_required_keys(self):
        for name in NAMES:
            with self.subTest(name=name):
                schema = json.loads((CONTRACTS / f"{name}.v1.schema.json").read_text(encoding="utf-8"))
                example = json.loads((CONTRACTS / "examples" / f"{name}.v1.example.json").read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertEqual(example["schema_version"], "1.0.0")
                self.assertTrue(set(schema["required"]).issubset(example.keys()))
                self.assertTrue(set(example.keys()).issubset(schema["properties"].keys()))
                self.assertTrue(example["requires_human_approval"])

    def test_original_generic_fixture_preserved(self):
        self.assertTrue((ROOT / "src/healthagent/workflow.py").is_file())
        self.assertTrue((ROOT / "data/synthetic/records.json").is_file())

if __name__ == "__main__":
    unittest.main()
