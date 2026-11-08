"""0.60.91 (D-O-097): verdict of a test and of a requirement from the results of the test plans.

    python -m unittest tests.test_testing_verification -v
"""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from modules.testing import verification as v  # noqa: E402


def run(test_id, proto, result):
    return {"test_id": test_id, "proto": proto, "result": result}


class VerdictTest(unittest.TestCase):
    def test_latest_result_per_prototype(self):
        rows = [run("T1", "P1", "failed"), run("T1", "P1", "passed")]  # re-tested after a fix: the later one counts
        self.assertEqual(v.verdicts(rows), {"T1": "passed"})

    def test_worst_prototype_wins(self):
        rows = [run("T1", "P1", "passed"), run("T1", "P2", "failed"), run("T2", "P1", "passed"), run("T2", "P2", "derogation"),
                run("T3", "P1", "abandoned")]
        self.assertEqual(v.verdicts(rows), {"T1": "failed", "T2": "derogation", "T3": "not_run"})

    def test_proto_names_ignore_case(self):
        self.assertEqual(v.verdicts([run("T1", "p1", "failed"), run("T1", "P1", "passed")]), {"T1": "passed"})

    def test_requirement_verdict(self):
        self.assertEqual(v.requirement_verdict([("A", "passed"), ("B", "passed")]), "verified")
        self.assertEqual(v.requirement_verdict([("A", "passed"), ("B", "derogation")]), "derogation")
        self.assertEqual(v.requirement_verdict([("A", "passed"), ("B", "not_run")]), "partial")
        self.assertEqual(v.requirement_verdict([("A", "not_run")]), "not_run")
        self.assertEqual(v.requirement_verdict([("A", "failed"), ("B", "not_run")]), "failed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
