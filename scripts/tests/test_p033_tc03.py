"""TC-P033-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc03", Path(__file__).resolve().parents[1] / "gates" / "p033_tc03.py"
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
_FORBIDDEN = {"qualified", "allowed"}


def payload(**overrides):
    base = {
        "lengthClass": "in-bounds",
        "declaredLength": 1024,
        "maxLength": 65536,
        "declaredWidth": 64,
        "declaredHeight": 48,
        "maxDimension": 8192,
        "bytesPresent": 1024,
        "headerTruncated": False,
        "allocateUnvalidated": False,
        "originalId": "source-original",
    }
    base.update(overrides)
    return base


class TcP03303(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-03")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertIn("original:source-original", result["preservedResults"])

    def test_repeat_declared_maximum_is_bounded(self):
        result = evaluate(
            payload(lengthClass="maximum", declaredLength=65536, bytesPresent=65536)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("reserved:65536", result["preservedResults"])
        self.assertIn("declared-length:65536", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("declared maximum", " ".join(_MODULE.REPEATS))

    def test_repeat_maximum_plus_one_reserves_nothing(self):
        result = evaluate(
            payload(lengthClass="maximum-plus-one", declaredLength=65537, bytesPresent=65536)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["impossible-length"])
        self.assertIn("reserved:0", result["preservedResults"])
        self.assertNotIn("reserved:65537", result["preservedResults"])
        self.assertIn("declared-length:65537", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_overflow_boundary_reserves_nothing(self):
        result = evaluate(
            payload(lengthClass="overflow", declaredLength=2**31, bytesPresent=16)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"bounded"})
        self.assertEqual(result["rejectedClaims"], ["integer-overflow"])
        self.assertIn("reserved:0", result["preservedResults"])
        self.assertNotIn("reserved:" + str(2**31), result["preservedResults"])
        self.assertIn("declared-length:" + str(2**31), result["preservedResults"])

    def test_repeat_truncated_header_reserves_nothing(self):
        result = evaluate(
            payload(lengthClass="truncated-header", headerTruncated=True, bytesPresent=4)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["truncated-header"])
        self.assertIn("reserved:0", result["preservedResults"])
        self.assertIn("bytes-present:4", result["preservedResults"])
        self.assertIn("original:source-original", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_impossible_dimension_reserves_nothing(self):
        result = evaluate(
            payload(lengthClass="impossible-dimension", declaredWidth=8193, declaredLength=128, bytesPresent=128)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["impossible-dimension"])
        self.assertIn("reserved:0", result["preservedResults"])
        self.assertIn("declared-dimension:8193x48", result["preservedResults"])
        self.assertIn("original:source-original", result["preservedResults"])

    def test_negative_unvalidated_length_is_not_allocated(self):
        result = evaluate(payload(allocateUnvalidated=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], _FORBIDDEN | {"bounded"})
        self.assertEqual(result["rejectedClaims"], ["unvalidated-length-allocation"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("reserved:0", result["preservedResults"])
        self.assertNotIn("reserved:1024", result["preservedResults"])
        self.assertIn("declared-length:1024", result["preservedResults"])
        self.assertIn("original:source-original", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "lengthClass": "huge"},
            {**valid, "declaredLength": -1},
            {**valid, "lengthClass": "maximum", "declaredLength": 65536, "bytesPresent": 10},
            {**valid, "lengthClass": "overflow", "declaredLength": 100},
            {**valid, "lengthClass": "truncated-header", "headerTruncated": False},
            {**valid, "headerTruncated": True},
            {**valid, "allocateUnvalidated": "yes"},
            {**valid, "originalId": " "},
            {**valid, "declaredWidth": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
