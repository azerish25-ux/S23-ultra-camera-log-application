"""TC-P036-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc03", Path(__file__).resolve().parents[1] / "gates" / "p036_tc03.py"
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_KEYS = (
    "caseId",
    "decision",
    "reasons",
    "rejectedClaims",
    "preservedResults",
    "openQuestions",
)
_FILE = "source-original.raw"


def payload(**overrides):
    base = {
        "declaredMaxBytes": 1024,
        "claimedLength": 512,
        "width": 64,
        "height": 48,
        "headerTruncated": False,
        "allocateFromUnvalidatedLength": False,
        "originalFile": _FILE,
    }
    base.update(overrides)
    return base


class TcP03603(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _FILE)

    def test_declared_maximum_is_bounded_and_keeps_the_file(self):
        result = evaluate(payload(claimedLength=1024))
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("declaredMax:1024", result["preservedResults"])
        self.assertIn("claimed:1024", result["preservedResults"])

    def test_maximum_plus_one_rejects_before_allocation(self):
        result = evaluate(payload(claimedLength=1025))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})
        self.assertIn("maximum-plus-one", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_integer_overflow_boundary_rejects_before_allocation(self):
        result = evaluate(payload(claimedLength=-1))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("integer-overflow-boundary", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)
        huge = evaluate(payload(claimedLength=2**63))
        self.assertEqual(huge["decision"], "rejected_before_alloc")
        self.assertIn("integer-overflow-boundary", huge["rejectedClaims"])
        self.assertIn(f"claimed:{2**63}", huge["preservedResults"])

    def test_truncated_header_rejects_before_read(self):
        result = evaluate(payload(headerTruncated=True, claimedLength=512))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("truncated-header", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)
        self.assertIn("dimensions:64x48", result["preservedResults"])

    def test_impossible_dimension_rejects_before_allocation(self):
        result = evaluate(payload(width=0, height=48))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("impossible-dimension", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)

    def test_negative_unvalidated_allocation_fails_and_keeps_the_file(self):
        result = evaluate(payload(allocateFromUnvalidatedLength=True, claimedLength=1025))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})
        self.assertIn("unvalidated-length-allocation", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)
        self.assertIn("claimed:1025", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "declaredMaxBytes": 0},
            {**valid, "claimedLength": "1024"},
            {**valid, "originalFile": ""},
            {**valid, "headerTruncated": 1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
