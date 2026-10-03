"""TC-P040-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc03", Path(__file__).resolve().parents[1] / "gates" / "p040_tc03.py"
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
_FILE = "take.raw"


def payload(**overrides):
    base = {
        "declaredMaxBytes": 4096,
        "claimedLength": 4096,
        "width": 64,
        "height": 48,
        "headerTruncated": False,
        "allocateFromUnvalidatedLength": False,
        "originalFile": _FILE,
    }
    base.update(overrides)
    return base


class TcP04003(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_FILE, result["preservedResults"])

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("impossible payload length", _MODULE.INTERVENTION)
        self.assertIn("preserving the original file", _MODULE.EXPECTED)
        self.assertIn("unvalidated length field", _MODULE.NEGATIVE)

    def test_declared_maximum_stays_bounded(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("declaredMax:4096", result["preservedResults"])
        self.assertIn("claimed:4096", result["preservedResults"])
        self.assertIn("dimensions:64x48", result["preservedResults"])

    def test_maximum_plus_one_rejects_before_allocation(self):
        result = evaluate(payload(claimedLength=4097))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertEqual(result["rejectedClaims"], ["maximum-plus-one"])
        self.assertIn(_FILE, result["preservedResults"])
        self.assertIn("claimed:4097", result["preservedResults"])
        self.assertIn("maximum plus one", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})

    def test_integer_overflow_boundary_rejects_before_allocation(self):
        result = evaluate(payload(claimedLength=2**63))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("integer-overflow-boundary", result["rejectedClaims"])
        self.assertIn(_FILE, result["preservedResults"])
        self.assertIn("integer overflow boundary", result["openQuestions"])

    def test_negative_length_is_an_overflow_boundary(self):
        result = evaluate(payload(claimedLength=-1))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("integer-overflow-boundary", result["rejectedClaims"])
        self.assertIn(_FILE, result["preservedResults"])

    def test_truncated_header_rejects_before_allocation(self):
        result = evaluate(payload(headerTruncated=True))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertEqual(result["rejectedClaims"], ["truncated-header"])
        self.assertIn(_FILE, result["preservedResults"])
        self.assertIn("truncated header", result["openQuestions"])

    def test_negative_unvalidated_length_allocation_fails(self):
        result = evaluate(payload(allocateFromUnvalidatedLength=True, claimedLength=10**12))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})
        self.assertEqual(result["rejectedClaims"], ["unvalidated-length-allocation"])
        self.assertIn(_FILE, result["preservedResults"])
        self.assertIn("claimed:" + str(10**12), result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_impossible_dimension_is_preserved_and_rejected(self):
        result = evaluate(payload(width=0))
        self.assertEqual(result["decision"], "rejected_before_alloc")
        self.assertIn("impossible-dimension", result["rejectedClaims"])
        self.assertIn("dimensions:0x48", result["preservedResults"])
        self.assertIn(_FILE, result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "originalFile"},
            {**valid, "extra": True},
            {**valid, "declaredMaxBytes": 0},
            {**valid, "claimedLength": True},
            {**valid, "originalFile": "  "},
            {**valid, "headerTruncated": "yes"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
