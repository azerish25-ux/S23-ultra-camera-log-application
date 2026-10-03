"""TC-P034-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc03", Path(__file__).resolve().parents[1] / "gates" / "p034_tc03.py"
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
        "lengthField": 4096,
        "width": 64,
        "height": 48,
        "maxDimension": 4096,
        "overflow": False,
        "truncatedHeader": False,
        "allocateFromLength": False,
        "originalFile": "take.s23raw",
    }
    base.update(overrides)
    return base


class TcP03403(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("file:take.s23raw", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_module_encodes_case_text(self):
        self.assertIn("impossible payload length", _MODULE.INTERVENTION)
        self.assertIn("preserving the original file", _MODULE.EXPECTED)
        self.assertIn("unvalidated length field", _MODULE.NEGATIVE)

    def test_declared_maximum_stays_bounded_and_keeps_the_file(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("length:4096", result["preservedResults"])
        self.assertIn("declared:4096", result["preservedResults"])

    def test_maximum_plus_one_rejects_before_allocation(self):
        result = evaluate(payload(lengthField=4097))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("length-exceeds-maximum", result["rejectedClaims"])
        self.assertIn("file:take.s23raw", result["preservedResults"])
        self.assertIn("length:4097", result["preservedResults"])

    def test_integer_overflow_boundary_rejects_a_small_wrapped_length(self):
        result = evaluate(payload(lengthField=16, overflow=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("integer-overflow", result["rejectedClaims"])
        self.assertIn("file:take.s23raw", result["preservedResults"])
        self.assertIn("dim:64x48", result["preservedResults"])

    def test_truncated_header_preserves_the_original_file(self):
        result = evaluate(payload(truncatedHeader=True, lengthField=100))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("truncated-header", result["rejectedClaims"])
        self.assertIn("file:take.s23raw", result["preservedResults"])

    def test_impossible_dimension_preserves_the_original_file(self):
        result = evaluate(payload(width=4097))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("impossible-dimension", result["rejectedClaims"])
        self.assertIn("file:take.s23raw", result["preservedResults"])
        self.assertIn("dim:4097x48", result["preservedResults"])

    def test_negative_unvalidated_length_allocation_fails(self):
        result = evaluate(payload(allocateFromLength=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})
        self.assertEqual(result["rejectedClaims"], ["unvalidated-length-allocation"])
        self.assertIn("file:take.s23raw", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(originalFile="a/b"))
        with self.assertRaises(ValueError):
            evaluate(payload(lengthField=-1))


if __name__ == "__main__":
    unittest.main()
