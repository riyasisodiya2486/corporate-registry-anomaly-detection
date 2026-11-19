"""Database-free tests of audit hash serialization and verification."""
import importlib
import io
import os
import unittest
from copy import deepcopy
from datetime import datetime
from contextlib import redirect_stdout
from unittest.mock import MagicMock, patch


class AuditVerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # SQLAlchemy engine construction is lazy; this dummy URL is never connected.
        with patch.dict(os.environ, {
            "DATABASE_URL": "postgresql+psycopg2://u:p@127.0.0.1:1/test"
        }):
            cls.audit = importlib.import_module("src.integrity.hash_chain")

    @classmethod
    def tearDownClass(cls):
        pass

    def make_row(self, log_id, action_type, cluster_id, reviewer, created_at, previous_hash):
        return {
            "log_id": log_id,
            "action_type": action_type,
            "cluster_id": cluster_id,
            "reviewer": reviewer,
            "created_at": created_at,
            "previous_hash": previous_hash,
            "action_hash": self.audit.compute_audit_action_hash(
                action_type, cluster_id, reviewer, created_at, previous_hash
            ),
        }

    def valid_rows(self):
        first_time = datetime(2025, 1, 2, 3, 4, 5, 123456)
        second_time = datetime(2025, 1, 2, 3, 5, 6, 654321)
        first = self.make_row(10, "flagged", 17, "system", first_time, "")
        second = self.make_row(
            11, "review:blind_queue:ordinary", 17, "reviewer-1",
            second_time, first["action_hash"],
        )
        return [first, second]

    def test_valid_multirow_chain(self):
        result = self.audit.verify_audit_chain_rows(self.valid_rows())
        self.assertEqual(result, {"valid": True, "count": 2})

    def test_modified_action_fields_or_timestamp_are_detected(self):
        for field, changed in (
            ("action_type", "escalated"),
            ("cluster_id", 18),
            ("reviewer", "changed-reviewer"),
            ("created_at", datetime(2025, 1, 2, 3, 4, 5, 123457)),
        ):
            with self.subTest(field=field):
                rows = self.valid_rows()
                rows[0][field] = changed
                result = self.audit.verify_audit_chain_rows(rows)
                self.assertFalse(result["valid"])
                self.assertEqual(result["log_id"], 10)
                self.assertIn("action_hash", result["reason"])

    def test_broken_previous_hash_is_reported_before_hash_comparison(self):
        rows = self.valid_rows()
        rows[1]["previous_hash"] = "tampered-previous"
        result = self.audit.verify_audit_chain_rows(rows)
        self.assertFalse(result["valid"])
        self.assertEqual(result["log_id"], 11)
        self.assertIn("previous_hash", result["reason"])

    def test_modified_stored_hash_is_detected(self):
        rows = self.valid_rows()
        rows[0]["action_hash"] = "tampered-hash"
        result = self.audit.verify_audit_chain_rows(rows)
        self.assertFalse(result["valid"])
        self.assertEqual(result["log_id"], 10)
        self.assertIn("action_hash", result["reason"])

    def test_empty_chain_is_valid(self):
        self.assertEqual(
            self.audit.verify_audit_chain_rows([]),
            {"valid": True, "count": 0},
        )

    def test_public_verifier_reports_empty_and_first_invalid_row(self):
        connection = MagicMock()
        engine = MagicMock()
        engine.connect.return_value.__enter__.return_value = connection

        connection.execute.return_value.mappings.return_value.all.return_value = []
        with redirect_stdout(io.StringIO()) as output:
            self.assertTrue(self.audit.verify_chain_integrity("audit_log", engine))
        self.assertIn("across 0 rows", output.getvalue())
        query = str(connection.execute.call_args.args[0]).lower()
        self.assertIn("created_at", query)

        rows = self.valid_rows()
        rows[1]["reviewer"] = "edited"
        connection.execute.return_value.mappings.return_value.all.return_value = rows
        with redirect_stdout(io.StringIO()) as output:
            self.assertFalse(self.audit.verify_chain_integrity("audit_log", engine))
        self.assertIn("log_id 11", output.getvalue())
        self.assertIn("action_hash", output.getvalue())

    def test_insert_and_verifier_use_the_same_timestamp_serialization(self):
        class Connection:
            def __init__(self):
                self.insert = None

            def execute(self, statement, params=None):
                sql = " ".join(str(statement).lower().split())
                if "pg_advisory_xact_lock" in sql:
                    return None
                if "select action_hash from audit_log" in sql:
                    return type("Result", (), {"fetchone": lambda self: None})()
                if "insert into audit_log" in sql:
                    self.insert = params
                    return None
                raise AssertionError(f"Unexpected SQL: {sql}")

        conn = Connection()
        action_hash = self.audit.log_audit_action(
            "reviewed", 5, "reviewer-a", connection=conn
        )
        self.assertEqual(
            self.audit.compute_audit_action_hash(
                conn.insert["at"], conn.insert["cid"], conn.insert["rev"],
                conn.insert["created_at"], conn.insert["ph"],
            ),
            action_hash,
        )
        self.assertEqual(action_hash, conn.insert["ah"])
        inserted_row = {
            "log_id": 1,
            "action_type": conn.insert["at"],
            "cluster_id": conn.insert["cid"],
            "reviewer": conn.insert["rev"],
            "created_at": conn.insert["created_at"],
            "action_hash": conn.insert["ah"],
            "previous_hash": conn.insert["ph"],
        }
        self.assertTrue(self.audit.verify_audit_chain_rows([inserted_row])["valid"])


if __name__ == "__main__":
    unittest.main()
