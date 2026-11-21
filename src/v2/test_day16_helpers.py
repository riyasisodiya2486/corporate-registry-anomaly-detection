"""Synthetic tests; the fake SQL engine does not establish PostgreSQL guarantees."""
import importlib
import io
import os
import tempfile
import unittest
from contextlib import contextmanager, redirect_stderr
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd

from src.v2.chain_reviews import chain_pending_reviews, main as chain_main
from src.v2.data_quality import (
    analyze_data_quality,
    main as data_quality_main,
    run_data_quality,
    validate_input_dir,
)
from src.v2.eval_dup_rule import evaluate_duplicate_rule
from src.v2.scaling_timing import (
    V2_ENTITIES,
    run_benchmark,
    run_blocking,
    run_scoring,
    save_scaling_plot,
)


class FakeResult:
    def __init__(self, rows=None, rowcount=0, one=None):
        self.rows = rows or []
        self.rowcount = rowcount
        self.one = one

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.one


class FakeConnection:
    def __init__(self, state, engine):
        self.state = state
        self.engine = engine

    def execute(self, statement, params=None):
        sql = " ".join(str(statement).lower().split())
        params = params or {}
        if "pg_advisory_xact_lock" in sql:
            self.engine.events.append(("lock", params.get("lock_id")))
            return FakeResult()
        if "from reviewer_reviews" in sql:
            self.engine.events.append(("select_reviews",))
            rows = [
                SimpleNamespace(**row)
                for row in sorted(self.state["reviews"], key=lambda item: item["review_id"])
                if row["chain_hash"] is None
            ]
            return FakeResult(rows)
        if "select action_hash from audit_log" in sql:
            self.engine.events.append(("select_audit_tail",))
            audit_log = self.state["audit_log"]
            return FakeResult(one=(audit_log[-1]["action_hash"],) if audit_log else None)
        if "insert into audit_log" in sql:
            self.engine.events.append(("insert_audit", params.copy()))
            if self.engine.fail_audit_insert:
                raise RuntimeError("synthetic audit insert failure")
            self.state["audit_log"].append({
                "action_hash": params["ah"],
                "previous_hash": params["ph"],
                "action_type": params["at"],
                "cluster_id": params["cid"],
                "reviewer": params["rev"],
            })
            return FakeResult(rowcount=1)
        if "update reviewer_reviews" in sql:
            self.engine.events.append(("update_review", params.copy()))
            if self.engine.fail_review_update:
                raise RuntimeError("synthetic review update failure")
            row = next(r for r in self.state["reviews"] if r["review_id"] == params["i"])
            if row["chain_hash"] is not None:
                return FakeResult(rowcount=0)
            row["chain_hash"] = params["h"]
            return FakeResult(rowcount=1)
        raise AssertionError(f"Unexpected synthetic SQL: {sql}")


class FakeEngine:
    """Transactional in-memory SQL double, not a PostgreSQL emulator."""
    def __init__(self, reviews):
        self.state = {"reviews": deepcopy(reviews), "audit_log": []}
        self.fail_audit_insert = False
        self.fail_review_update = False
        self.commits = 0
        self.rollbacks = 0
        self.events = []

    @contextmanager
    def begin(self):
        working_state = deepcopy(self.state)
        connection = FakeConnection(working_state, self)
        try:
            yield connection
        except Exception:
            self.rollbacks += 1
            raise
        else:
            self.state = working_state
            self.commits += 1


def sample_reviews():
    return [
        {"review_id": 2, "cluster_id": 22, "reviewer": "reviewer-b",
         "review_mode": "blind_queue", "verdict": "ordinary", "chain_hash": None},
        {"review_id": 1, "cluster_id": 11, "reviewer": "reviewer-a",
         "review_mode": "blind_queue", "verdict": "worth_review", "chain_hash": None},
    ]


class AuditChainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # create_engine is lazy; this dummy URL is never connected to.
        with patch.dict(os.environ, {"DATABASE_URL": "postgresql+psycopg2://u:p@127.0.0.1:1/test"}):
            cls.audit_module = importlib.import_module("src.integrity.hash_chain")

    @classmethod
    def tearDownClass(cls):
        pass

    def test_multiple_reviews_lock_log_and_update_in_order(self):
        engine = FakeEngine(sample_reviews())
        count = chain_pending_reviews(engine, self.audit_module.log_audit_action)

        self.assertEqual(count, 2)
        self.assertEqual(engine.commits, 1)
        self.assertEqual(engine.rollbacks, 0)
        self.assertEqual([r["review_id"] for r in sorted(engine.state["reviews"], key=lambda r: r["review_id"])], [1, 2])
        self.assertTrue(all(r["chain_hash"] for r in engine.state["reviews"]))
        self.assertEqual(len(engine.state["audit_log"]), 2)
        self.assertEqual(engine.state["audit_log"][0]["previous_hash"], "")
        self.assertEqual(
            engine.state["audit_log"][1]["previous_hash"],
            engine.state["audit_log"][0]["action_hash"],
        )

        event_names = [event[0] for event in engine.events]
        self.assertEqual(event_names[0:2], ["lock", "select_reviews"])
        for start in (2, 6):
            self.assertEqual(
                event_names[start:start + 4],
                ["lock", "select_audit_tail", "insert_audit", "update_review"],
            )

    def test_audit_insert_failure_rolls_back_entire_batch(self):
        engine = FakeEngine(sample_reviews())
        before = deepcopy(engine.state)
        engine.fail_audit_insert = True
        with self.assertRaisesRegex(RuntimeError, "audit insert failure"):
            chain_pending_reviews(engine, self.audit_module.log_audit_action)
        self.assertEqual(engine.state, before)
        self.assertEqual(engine.rollbacks, 1)

    def test_review_update_failure_rolls_back_audit_insert_and_batch(self):
        engine = FakeEngine(sample_reviews())
        before = deepcopy(engine.state)
        engine.fail_review_update = True
        with self.assertRaisesRegex(RuntimeError, "review update failure"):
            chain_pending_reviews(engine, self.audit_module.log_audit_action)
        self.assertEqual(engine.state, before)
        self.assertEqual(engine.rollbacks, 1)

    def test_repeated_execution_does_not_add_duplicate_audit_rows(self):
        engine = FakeEngine(sample_reviews())
        self.assertEqual(chain_pending_reviews(engine, self.audit_module.log_audit_action), 2)
        audit_rows = deepcopy(engine.state["audit_log"])
        self.assertEqual(chain_pending_reviews(engine, self.audit_module.log_audit_action), 0)
        self.assertEqual(engine.state["audit_log"], audit_rows)
        self.assertEqual(engine.commits, 2)

    def test_existing_db_engine_call_form_remains_supported(self):
        engine = FakeEngine([])
        action_hash = self.audit_module.log_audit_action(
            "synthetic", 7, "reviewer-x", db_engine=engine
        )
        self.assertEqual(engine.commits, 1)
        self.assertEqual(engine.state["audit_log"][0]["action_hash"], action_hash)

    def test_main_disposes_v2_engine_when_chaining_fails(self):
        dummy_url = "postgresql+psycopg2://u:p@127.0.0.1:1/test"
        fake_engine = SimpleNamespace(url=dummy_url, dispose=Mock())
        with patch("src.v2.chain_reviews.create_engine", return_value=fake_engine), \
             patch.dict(os.environ, {"V2_DATABASE_URL": dummy_url, "DATABASE_URL": ""}), \
             patch("src.v2.chain_reviews.chain_pending_reviews", side_effect=RuntimeError("synthetic")):
            with self.assertRaisesRegex(RuntimeError, "synthetic"):
                chain_main()
            fake_engine.dispose.assert_called()

    def test_main_refuses_same_v2_and_default_database_url(self):
        url = "postgresql+psycopg2://u:p@127.0.0.1:1/test"
        with patch.dict(os.environ, {"V2_DATABASE_URL": url, "DATABASE_URL": url}):
            with self.assertRaisesRegex(SystemExit, "must be distinct"):
                chain_main()


class ScalingTimingTests(unittest.TestCase):
    def setUp(self):
        self.entities = pd.DataFrame(
            [
                (1, "123456", "acme company limited", "12 market road pune"),
                (2, "123456", "acme company private limited", "12 market road pune"),
                (3, "654321", "other business limited", "8 station road pune"),
                (4, "654321", "other business private limited", "8 station road pune"),
                (5, "000001", "separate trading limited", "9 hill road pune"),
                (6, "000002", "sample works limited", "1 lake road pune"),
                (7, "000003", "north services limited", "4 park road pune"),
                (8, "000004", "south exports limited", "7 garden road pune"),
            ],
            columns=["entity_id", "pincode", "company_name_normalized", "address_normalized"],
        )

    def test_blocker_and_scorer_signatures_work_with_synthetic_rows(self):
        pairs = run_blocking(self.entities.iloc[:2])
        self.assertEqual(list(pairs.columns[:3]), ["pair_id", "entity_id_a", "entity_id_b"])
        self.assertGreater(len(pairs), 0)
        scores = run_scoring(pairs, self.entities.iloc[:2])
        self.assertEqual(list(scores.columns), ["pair_id", "address_similarity", "name_similarity", "is_match"])
        self.assertTrue(scores.is_match.any())

    def test_valid_no_candidate_subset_returns_empty_pair_schema(self):
        no_pairs = pd.DataFrame(
            [
                (1, "100001", "alpha company", "1 road"),
                (2, "100002", "bravo company", "2 road"),
                (3, "100003", "charlie company", "3 road"),
            ],
            columns=self.entities.columns,
        )
        pairs = run_blocking(no_pairs)
        self.assertTrue(pairs.empty)
        self.assertEqual(list(pairs.columns), ["pair_id", "entity_id_a", "entity_id_b"])
        self.assertTrue(run_scoring(pairs, no_pairs).empty)

    def test_duplicate_or_null_entity_ids_are_rejected(self):
        duplicate = pd.concat([self.entities.iloc[:1], self.entities.iloc[:1]])
        with self.assertRaisesRegex(ValueError, "unique"):
            run_blocking(duplicate)
        null_id = self.entities.iloc[:2].copy()
        null_id.loc[null_id.index[0], "entity_id"] = None
        with self.assertRaisesRegex(ValueError, "null"):
            run_blocking(null_id)

    def test_benchmark_has_sorted_seeded_nested_subsets_and_consistent_times(self):
        reversed_rows = self.entities.iloc[::-1].reset_index(drop=True)
        result = run_benchmark(reversed_rows)
        self.assertEqual(result.fraction.tolist(), [0.25, 0.5, 0.75, 1.0])
        self.assertEqual(result.records.tolist(), [2, 4, 6, 8])
        self.assertTrue(
            all(
                total == round(blocking + scoring, 4)
                for total, blocking, scoring in zip(
                    result.total_s, result.blocking_s, result.scoring_s
                )
            )
        )
        self.assertEqual(V2_ENTITIES.as_posix(), "results/v2/cleaned_entities.csv")

    def test_sampling_is_nested_and_stable_when_csv_rows_are_reordered(self):
        from src.v2 import scaling_timing

        captures = []

        def capture_blocking(subset):
            captures.append(tuple(sorted(subset.entity_id.tolist())))
            return pd.DataFrame(columns=["pair_id", "entity_id_a", "entity_id_b"])

        with patch.object(scaling_timing, "run_blocking", side_effect=capture_blocking), \
             patch.object(scaling_timing, "run_scoring", return_value=pd.DataFrame()):
            run_benchmark(self.entities)
            first = captures[:]
            captures.clear()
            run_benchmark(self.entities.iloc[::-1])
            second = captures[:]
        self.assertEqual(first, second)
        self.assertTrue(set(first[0]).issubset(first[1]))
        self.assertTrue(set(first[1]).issubset(first[2]))
        self.assertTrue(set(first[2]).issubset(first[3]))

    def test_scaling_plot_closes_its_figure(self):
        import matplotlib

        matplotlib.use("Agg", force=True)
        import matplotlib.pyplot as plt

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "scaling.png"
            save_scaling_plot(
                pd.DataFrame({"records": [1, 2], "total_s": [0.1, 0.2]}), path
            )
            self.assertTrue(path.is_file())
            self.assertEqual(plt.get_fignums(), [])


class DuplicateEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.labels = pd.DataFrame({"pair_id": [1, 2, 3, 4], "label": ["y", "n", "y", "n"]})
        self.flags = pd.DataFrame({"pair_id": [1, 2, 3, 4], "rule_flag": [True, True, False, False]})

    def test_exact_y_n_labels_are_evaluated(self):
        result = evaluate_duplicate_rule(self.labels, self.flags)
        self.assertEqual(result["flagged_pairs"], 2)
        self.assertEqual(result["true_duplicates_flagged"], 1)
        self.assertEqual(result["rule_precision"], 0.5)
        self.assertEqual(result["near_miss_positive_rate"], 0.5)

    def test_only_exact_lowercase_labels_are_accepted(self):
        for invalid in ("yes", "Y", " y", "n ", "", None):
            with self.subTest(label=invalid):
                labels = pd.DataFrame({"pair_id": [1], "label": [invalid]})
                flags = pd.DataFrame({"pair_id": [1], "rule_flag": [True]})
                with self.assertRaises(ValueError):
                    evaluate_duplicate_rule(labels, flags)

    def test_null_pair_ids_are_rejected_in_either_file(self):
        for frame_name in ("labels", "flags"):
            with self.subTest(frame=frame_name):
                labels, flags = self.labels.iloc[:1].copy(), self.flags.iloc[:1].copy()
                target = labels if frame_name == "labels" else flags
                target["pair_id"] = pd.Series([None], dtype=object)
                with self.assertRaisesRegex(ValueError, "null or blank"):
                    evaluate_duplicate_rule(labels, flags)

    def test_duplicate_pair_ids_are_rejected_in_either_file(self):
        labels = pd.DataFrame({"pair_id": [1, 1], "label": ["y", "n"]})
        flags = pd.DataFrame({"pair_id": [1], "rule_flag": [True]})
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_duplicate_rule(labels, flags)
        labels = pd.DataFrame({"pair_id": [1, "1"], "label": ["y", "n"]})
        flags = pd.DataFrame({"pair_id": [1, 2], "rule_flag": [True, False]})
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_duplicate_rule(labels, flags)
        labels = self.labels.iloc[:1].copy()
        flags = pd.DataFrame({"pair_id": [1, 1], "rule_flag": [True, False]})
        with self.assertRaisesRegex(ValueError, "unique"):
            evaluate_duplicate_rule(labels, flags)

    def test_invalid_rule_flags_are_rejected(self):
        for invalid in (None, "true", 2, 1.0):
            with self.subTest(flag=invalid):
                flags = pd.DataFrame({"pair_id": [1], "rule_flag": [invalid]})
                with self.assertRaisesRegex(ValueError, "boolean"):
                    evaluate_duplicate_rule(self.labels.iloc[:1], flags)

    def test_mismatched_pair_sets_are_rejected(self):
        flags = self.flags.iloc[:3].copy()
        with self.assertRaisesRegex(ValueError, "same pair_id"):
            evaluate_duplicate_rule(self.labels, flags)


class DataQualitySafetyTests(unittest.TestCase):
    @staticmethod
    def write_input_files(directory):
        directory.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(
            [
                (1, "acme company limited", "shared road", "100001", "2020-01-01"),
                (2, "acme company limited", "shared road", "100001", "2020-01-03"),
                (3, "third firm limited", "shared road", "100002", "2021-02-01"),
                (4, "fourth firm limited", "shared road", "100003", "2022-03-01"),
            ],
            columns=["entity_id", "company_name_normalized", "address_normalized", "pincode", "date_of_registration"],
        ).to_csv(directory / "cleaned_entities.csv", index=False)
        pd.DataFrame({"entity_id": [1, 2, 3, 4], "cluster_id": [10, 10, 20, 30]}).to_csv(
            directory / "cluster_assignments.csv", index=False
        )
        pd.DataFrame({
            "cluster_id": [10, 20, 30],
            "flag_category": ["high_priority", "moderate", "baseline"],
            "composite_score": [80.0, 50.0, 10.0],
        }).to_csv(directory / "cluster_scores.csv", index=False)

    def test_input_directory_must_be_explicit_and_never_defaults_to_v1(self):
        with patch.dict(os.environ, {"V2_INPUT_DIR": ""}):
            with redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    data_quality_main([])
        with self.assertRaisesRegex(ValueError, "V1 snapshot"):
            validate_input_dir(Path(__file__).resolve().parents[2] / "results" / "snapshot")
        with self.assertRaisesRegex(ValueError, "snapshot and backup"):
            validate_input_dir(
                Path(__file__).resolve().parents[2]
                / "results"
                / "snapshot_backup_20261024"
            )

    def test_missing_files_are_rejected_before_output_directory_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir, output_dir = root / "input", root / "output"
            input_dir.mkdir()
            with self.assertRaises(FileNotFoundError):
                run_data_quality(input_dir, output_dir)
            self.assertFalse(output_dir.exists())

    def test_missing_columns_are_rejected_before_full_read_or_output_creation(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir, output_dir = root / "input", root / "output"
            self.write_input_files(input_dir)
            pd.DataFrame({"wrong": [1]}).to_csv(input_dir / "cluster_scores.csv", index=False)
            with self.assertRaisesRegex(ValueError, "cluster_scores.csv"):
                run_data_quality(input_dir, output_dir)
            self.assertFalse(output_dir.exists())

    def test_header_validation_and_synthetic_run_use_only_explicit_temp_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            input_dir, output_dir = root / "v2_input", root / "v2_output"
            self.write_input_files(input_dir)
            _, address_column = validate_input_dir(input_dir)
            self.assertEqual(address_column, "address_normalized")
            summary = run_data_quality(input_dir, output_dir)
            self.assertEqual(len(summary), 3)
            self.assertTrue((output_dir / "dup_pairs.csv").is_file())
            self.assertTrue((output_dir / "cluster_dq.csv").is_file())
            self.assertTrue((output_dir / "placeholder_top50.csv").is_file())


if __name__ == "__main__":
    unittest.main()
