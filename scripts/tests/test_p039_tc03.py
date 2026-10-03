"""TC-P039-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc03", Path(__file__).resolve().parents[1] / "gates" / "p039_tc03.py"
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
        "declaredMaximum": 1024,
        "lengthField": "1024",
        "headerBytes": 64,
        "requiredHeaderBytes": 64,
        "boundary": "declared_maximum",
        "allocateUnvalidated": False,
        "originalFile": "take.rawseq",
    }
    base.update(overrides)
    return base


class TcP03903(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_declared_maximum_does_not_allocate(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded_accept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("file:take.rawseq", result["preservedResults"])
        self.assertIn("declaredMaximum:1024", result["preservedResults"])

    def test_maximum_plus_one_rejects_before_allocation(self):
        result = evaluate(payload(lengthField="1025", boundary="maximum_plus_one"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("oversized-record", result["rejectedClaims"])
        self.assertIn("file:take.rawseq", result["preservedResults"])
        self.assertIn("length:1025", result["preservedResults"])

    def test_integer_overflow_boundary_rejects(self):
        result = evaluate(payload(lengthField="2147483648", boundary="integer_overflow"))
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("integer-overflow-length", result["rejectedClaims"])
        self.assertIn("file:take.rawseq", result["preservedResults"])

    def test_truncated_header_rejects_and_keeps_the_file(self):
        result = evaluate(payload(headerBytes=8, boundary="truncated_header"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("truncated-header", result["rejectedClaims"])
        self.assertIn("headerBytes:8", result["preservedResults"])
        self.assertIn("file:take.rawseq", result["preservedResults"])

    def test_unvalidated_length_allocation_is_rejected(self):
        result = evaluate(payload(allocateUnvalidated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unvalidated-length-allocation", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("file:take.rawseq", result["preservedResults"])


if __name__ == "__main__":
    unittest.main()
