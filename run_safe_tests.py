"""Run all database-free tests in the repository.

These tests use mocks/fakes or pure functions only. They never connect to a
database, never touch production data, and never run destructive SQL.

Usage:
    python run_safe_tests.py
"""
import os
import sys
import unittest

# Ensure the project root is importable when run from any directory.
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Modules that are safe to import and test without a database.
SAFE_TEST_MODULES = [
    "src.v2.test_day16_helpers",
    "src.integrity.test_audit_verification",
]


def main() -> int:
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    for module_name in SAFE_TEST_MODULES:
        try:
            suite.addTests(loader.loadTestsFromName(module_name))
        except Exception as exc:  # pragma: no cover - defensive
            print(f"WARNING: could not load {module_name}: {exc}")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())