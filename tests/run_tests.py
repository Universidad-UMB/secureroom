"""Unified Test Runner for SecureRoom v1."""

import os
import sys
import unittest


def run_all_suites():
    print("================================================================")
    print("       SecureRoom v1 — Automated Test Suite Runner")
    print("================================================================")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Discover tests across all categories
    for sub in ["unit", "integration", "security"]:
        sub_dir = os.path.join(current_dir, sub)
        sub_suite = loader.discover(start_dir=sub_dir, top_level_dir=project_root)
        suite.addTests(sub_suite)

    print(f"Executing tests across unit, integration, and security suites...\n")

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n================================================================")
    print(f"Tests run: {result.testsRun}")
    print(f"Errors: {len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print("================================================================")

    if result.wasSuccessful():
        print("ALL TESTS PASSED SUCCESSFULLY!")
        return 0
    else:
        print("SOME TESTS FAILED.")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_suites())
