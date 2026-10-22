"""Offline unit tests for post-kickoff read-only synthetic TB Zetaris probe."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.careflow.tb_zetaris_probe import (
    BUSINESS_IDS, EVIDENCE_SOURCES, PROVENANCE_IDS, main, probe_case,
    summarize_source_rows,
)
from shared.zetaris.readonly import (
    ZetarisHelperClient, ZetarisQueryError, case_query, parse_query_rows,
    validate_readonly_select,
)


class QuerySafetyTests(unittest.TestCase):
    def test_case_query_bounded_and_allowlisted(self):
        self.assertEqual(
            case_query("TB_TEAM", "lab_results", "CASE-TB-001", limit=4),
            "SELECT * FROM TB_TEAM.lab_results WHERE case_id = 'CASE-TB-001' LIMIT 4",
        )

    def test_disallows_sql_injection_and_untrusted_sources(self):
        for candidate in ("TB'; DELETE FROM x; --", "tb' OR '1'='1", "a.b"):
            with self.subTest(case_id=candidate), self.assertRaises(ValueError):
                case_query("TB_TEAM", "cases", candidate)
        for name in ("ground_truth_holdout", "users", "cases; DROP TABLE x"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                case_query("TB_TEAM", name, "CASE-TB-001")
        with self.assertRaises(ValueError):
            case_query("TB_TEAM;DROP", "cases", "CASE-TB-001")

    def test_rejects_mutations_comments_and_multi_statements(self):
        for sql in ("DROP TABLE x", "SELECT 1; DELETE FROM x", "SELECT 1 -- comment",
                    "SELECT * FROM ground_truth_holdout", "SELECT x INTO target FROM cases"):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_readonly_select(sql)
        self.assertEqual(validate_readonly_select("SELECT 1;"), "SELECT 1")

    def test_rejects_unrelated_tables_and_unions(self):
        for sql in (
            "SELECT * FROM PRIVATE.real_patients",
            "SELECT * FROM TB_TEAM.cases WHERE case_id = 'CASE-TB-001' LIMIT 5 UNION SELECT * FROM x",
            "SELECT * FROM TB_TEAM.cases",
        ):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_readonly_select(sql)

    def test_limits(self):
        for limit in (0, 501):
            with self.assertRaises(ValueError):
                case_query("TB_TEAM", "cases", "CASE-TB-001", limit=limit)


class ResponseParsingTests(unittest.TestCase):
    def test_json_rows(self):
        self.assertEqual(parse_query_rows({"data": [{"ingest_row_id": "R-1"}]}),
                         [{"ingest_row_id": "R-1"}])
        self.assertEqual(parse_query_rows({"data": []}), [])

    def test_rows_with_column_metadata(self):
        payload = {"data": {"columns": [{"name": "ingest_row_id"}], "rows": [["R-2"]]}}
        self.assertEqual(parse_query_rows(payload), [{"ingest_row_id": "R-2"}])

    def test_unknown_success_shape_is_not_absence(self):
        with self.assertRaises(ZetarisQueryError) as ctx:
            parse_query_rows({"something": 1})
        self.assertEqual(ctx.exception.category, "invalid_response")


class ProbeTests(unittest.TestCase):
    def test_source_statuses_remain_distinct(self):
        class Fake:
            def query(self, sql):
                if ".lab_results " in sql:
                    raise ZetarisQueryError("temporarily_unavailable", "outage")
                if ".lab_orders " in sql:
                    return [{"case_id": "CASE-TB-001", "ingest_row_id": "ROW-ORD-001-A",
                             "order_id": "ORD-TB-001"}]
                return []
        result = probe_case(Fake(), namespace="TB_TEAM", case_id="CASE-TB-001")
        by_source = {entry["source"]: entry for entry in result["sources"]}
        self.assertEqual(set(by_source), set(EVIDENCE_SOURCES))
        self.assertNotIn("source_checks", by_source)
        self.assertEqual(by_source["lab_results"]["status"], "temporarily_unavailable")
        self.assertIsNone(by_source["lab_results"]["row_count"])
        self.assertEqual(by_source["cases"]["status"], "not_found")
        self.assertEqual(by_source["lab_orders"]["source_record_ids"], ["ROW-ORD-001-A"])
        self.assertEqual(by_source["lab_orders"]["business_event_ids"], ["ORD-TB-001"])
        self.assertFalse(result["visibility_simulation_applied"])
        self.assertTrue(result["requires_human_approval"])

    def test_tb_v1_columns_are_used_for_all_five_sources(self):
        for source in EVIDENCE_SOURCES:
            with self.subTest(source=source):
                record = {"case_id": "CASE-TB-001"}
                record[PROVENANCE_IDS[source]] = "ROW-123" if source != "cases" else "CASE-TB-001"
                record[BUSINESS_IDS[source]] = "BUSINESS-123" if source != "cases" else "CASE-TB-001"
                result = summarize_source_rows([record], source=source, case_id="CASE-TB-001")
                self.assertEqual(result["row_count"], 1)
                self.assertEqual(len(result["source_record_ids"]), 1)
                self.assertEqual(len(result["business_event_ids"]), 1)

    def test_duplicate_business_event_keeps_both_ingest_provenance_ids(self):
        rows = [
            {"case_id": "CASE-TB-001", "ingest_row_id": "ROW-A", "result_id": "RES-001"},
            {"case_id": "CASE-TB-001", "ingest_row_id": "ROW-B", "result_id": "RES-001"},
        ]
        summary = summarize_source_rows(rows, source="lab_results", case_id="CASE-TB-001")
        self.assertEqual(summary["source_record_ids"], ["ROW-A", "ROW-B"])
        self.assertEqual(summary["business_event_ids"], ["RES-001", "RES-001"])

    def test_mismatched_case_or_missing_provenance_does_not_look_empty(self):
        for record in (
            {"case_id": "CASE-TB-999", "ingest_row_id": "ROW-A", "order_id": "ORD-A"},
            {"case_id": "CASE-TB-001", "order_id": "ORD-A"},
        ):
            with self.subTest(record=record), self.assertRaises(ZetarisQueryError):
                summarize_source_rows([record], source="lab_orders", case_id="CASE-TB-001")

    def test_dry_run_returns_without_helper_or_credentials(self):
        from contextlib import redirect_stdout
        from io import StringIO
        stream = StringIO()
        with redirect_stdout(stream):
            code = main(["--case-id", "CASE-TB-001", "--namespace", "TB_TEAM", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(stream.getvalue())["queries"]), 5)

    def test_helper_is_not_used_to_execute_write_sql(self):
        with TemporaryDirectory() as directory:
            helper = Path(directory) / "query_zetaris.py"
            helper.write_text("# mock", encoding="utf-8")
            client = ZetarisHelperClient(helper)
            with patch("subprocess.run") as runner:
                with self.assertRaises(ValueError):
                    client.query("DELETE FROM tb")
                runner.assert_not_called()

    def test_helper_success_and_permission_failure(self):
        with TemporaryDirectory() as directory:
            helper = Path(directory) / "query_zetaris.py"
            helper.write_text("# mock", encoding="utf-8")
            client = ZetarisHelperClient(helper)
            class Completed:
                def __init__(self, rc, stdout, stderr=""):
                    self.returncode = rc
                    self.stdout = stdout
                    self.stderr = stderr
            with patch("subprocess.run", return_value=Completed(0, '{"data": [{"case_id": "CASE-TB-001"}]}')):
                self.assertEqual(client.query("SELECT 1"), [{"case_id": "CASE-TB-001"}])
            with patch("subprocess.run", return_value=Completed(1, "", "HTTP 403")):
                with self.assertRaises(ZetarisQueryError) as ctx:
                    client.query("SELECT 1")
                self.assertEqual(ctx.exception.category, "permission_denied")


if __name__ == "__main__":
    unittest.main()
