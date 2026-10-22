"""Offline unit tests for new post-kickoff read-only sponsor adapter."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from apps.careflow.tb_zetaris_probe import main, probe_case
from shared.zetaris.readonly import (
    ALLOWED_SOURCES, ZetarisHelperClient, ZetarisQueryError,
    case_query, parse_query_rows, validate_readonly_select,
)


class QuerySafetyTests(unittest.TestCase):
    def test_case_query_bounded_and_allowlisted(self):
        self.assertEqual(
            case_query("TB_TEAM", "lab_results", "TB-001", limit=4),
            "SELECT * FROM TB_TEAM.lab_results WHERE case_id = 'TB-001' LIMIT 4",
        )

    def test_disallows_sql_injection_and_untrusted_sources(self):
        for kw in ("TB'; DELETE FROM x; --", "tb' OR '1'='1", "a.b"):
            with self.subTest(kw=kw), self.assertRaises(ValueError):
                case_query("TB_TEAM", "cases", kw)
        for name in ("ground_truth_holdout", "users", "cases; DROP TABLE x"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                case_query("TB_TEAM", name, "TB-001")
        with self.assertRaises(ValueError):
            case_query("TB_TEAM;DROP", "cases", "TB-001")

    def test_rejects_mutations_comments_and_multi_statements(self):
        for sql in ("DROP TABLE x", "SELECT 1; DELETE FROM x", "SELECT 1 -- comment",
                    "SELECT * FROM ground_truth_holdout", "SELECT x INTO target FROM cases"):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_readonly_select(sql)
        self.assertEqual(validate_readonly_select("SELECT 1;"), "SELECT 1")

    def test_rejects_unrelated_tables_and_unions(self):
        for sql in (
            "SELECT * FROM PRIVATE.real_patients",
            "SELECT * FROM TB_TEAM.cases WHERE case_id = 'TB-001' LIMIT 5 UNION SELECT * FROM x",
            "SELECT * FROM TB_TEAM.cases",
        ):
            with self.subTest(sql=sql), self.assertRaises(ValueError):
                validate_readonly_select(sql)

    def test_limits(self):
        for limit in (0, 501):
            with self.assertRaises(ValueError):
                case_query("TB_TEAM", "cases", "TB-001", limit=limit)


class ResponseParsingTests(unittest.TestCase):
    def test_json_rows(self):
        self.assertEqual(parse_query_rows({"data": [{"source_record_id": "R-1"}]}),
                         [{"source_record_id": "R-1"}])
        self.assertEqual(parse_query_rows({"data": []}), [])

    def test_rows_with_column_metadata(self):
        payload = {"data": {"columns": [{"name": "source_record_id"}], "rows": [["R-2"]]}}
        self.assertEqual(parse_query_rows(payload), [{"source_record_id": "R-2"}])

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
                    return [{"source_record_id": "L-4"}]
                return []
        result = probe_case(Fake(), namespace="TB_TEAM", case_id="TB-001")
        by_source = {x["source"]: x for x in result["sources"]}
        self.assertEqual(set(by_source), set(ALLOWED_SOURCES))
        self.assertEqual(by_source["lab_results"]["status"], "temporarily_unavailable")
        self.assertIsNone(by_source["lab_results"]["row_count"])
        self.assertEqual(by_source["cases"]["status"], "not_found")
        self.assertEqual(by_source["lab_orders"]["source_record_ids"], ["L-4"])
        self.assertTrue(result["requires_human_approval"])

    def test_dry_run_returns_without_helper_or_credentials(self):
        from contextlib import redirect_stdout
        from io import StringIO
        stream = StringIO()
        with redirect_stdout(stream):
            code = main(["--case-id", "TB-001", "--namespace", "TB_TEAM", "--dry-run"])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(stream.getvalue())["queries"]), 6)

    def test_helper_is_not_used_to_execute_write_sql(self):
        with TemporaryDirectory() as d:
            helper = Path(d) / "query_zetaris.py"
            helper.write_text("# mocked official helper", encoding="utf-8")
            client = ZetarisHelperClient(helper)
            with patch("subprocess.run") as runner:
                with self.assertRaises(ValueError):
                    client.query("DELETE FROM tb")
                runner.assert_not_called()

    def test_helper_success_and_permission_failure(self):
        with TemporaryDirectory() as d:
            helper = Path(d) / "query_zetaris.py"
            helper.write_text("# mock", encoding="utf-8")
            client = ZetarisHelperClient(helper)
            class Completed:
                def __init__(self, rc, stdout, stderr=""):
                    self.returncode = rc
                    self.stdout = stdout
                    self.stderr = stderr
            with patch("subprocess.run", return_value=Completed(0, '{"data": [{"record_id": "R1"}]}')):
                self.assertEqual(client.query("SELECT 1"), [{"record_id": "R1"}])
            with patch("subprocess.run", return_value=Completed(1, "", "HTTP 403")):
                with self.assertRaises(ZetarisQueryError) as ctx:
                    client.query("SELECT 1")
                self.assertEqual(ctx.exception.category, "permission_denied")


if __name__ == "__main__":
    unittest.main()
