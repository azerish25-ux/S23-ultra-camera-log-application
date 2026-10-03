"""TC-P037-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc03", Path(__file__).resolve().parents[1] / "gates" / "p037_tc03.py"
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


def payload(**overrides):
    base = {
        "declaredMaximum": 4096,
        "lengthField": "4096",
        "headerBytes": 64,
        "requiredHeaderBytes": 64,
        "boundary": "declared_maximum",
        "allocateUnvalidated": False,
        "originalFile": "take.raw",
    }
    base.update(overrides)
    return base


class TcP03703(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_declared_maximum_accepts_without_qualification(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded_accept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("file:take.raw", result["preservedResults"])
        self.assertIn("length:4096", result["preservedResults"])

    def test_maximum_plus_one_rejects_and_keeps_the_file(self):
        result = evaluate(payload(lengthField="4097", boundary="maximum_plus_one"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("oversized-record", result["rejectedClaims"])
        self.assertIn("file:take.raw", result["preservedResults"])
        self.assertIn("original file was not rewritten", result["openQuestions"])

    def test_integer_overflow_boundary_rejects_before_allocation(self):
        result = evaluate(payload(lengthField="2147483648", boundary="integer_overflow"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("integer-overflow-length", result["rejectedClaims"])
        self.assertIn("file:take.raw", result["preservedResults"])
        self.assertTrue(any("before allocation" in item for item in result["reasons"]))

    def test_truncated_header_rejects(self):
        result = evaluate(payload(headerBytes=8, boundary="truncated_header"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("truncated-header", result["rejectedClaims"])
        self.assertIn("headerBytes:8", result["preservedResults"])
        self.assertIn("file:take.raw", result["preservedResults"])

    def test_unvalidated_length_allocation_fails(self):
        result = evaluate(payload(allocateUnvalidated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded_accept"})
        self.assertIn("unvalidated-length-allocation", result["rejectedClaims"])
        self.assertIn("file:take.raw", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_negative_length_is_an_overflow_boundary(self):
        result = evaluate(payload(lengthField="-1", boundary="integer_overflow"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("length:-1", result["preservedResults"])
        self.assertIn("file:take.raw", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "lengthField": "04096"},
            {**valid, "boundary": "maximum_plus_one"},
            {**valid, "allocateUnvalidated": 1},
            {**valid, "originalFile": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
