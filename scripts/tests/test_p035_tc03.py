"""TC-P035-03 oversized source record."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc03", Path(__file__).resolve().parents[1] / "gates" / "p035_tc03.py"
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
        "declaredLength": "4096",
        "declaredWidth": 4,
        "declaredHeight": 4,
        "maximumBytes": 4096,
        "headerComplete": True,
        "fileToken": "src-sha256:abc",
        "allocateUnvalidated": False,
    }
    base.update(overrides)
    return base


class TcP03503(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_repeat_declared_maximum_is_bounded_without_allocation(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("file:src-sha256:abc", result["preservedResults"])
        self.assertIn("declared-length:4096", result["preservedResults"])
        self.assertNotIn("allocated:4096", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_maximum_plus_one(self):
        result = evaluate(payload(declaredLength="4097"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("over-maximum", result["rejectedClaims"])
        self.assertIn("file:src-sha256:abc", result["preservedResults"])
        self.assertIn("declared-size:4x4", result["preservedResults"])

    def test_repeat_integer_overflow_boundary(self):
        result = evaluate(payload(declaredLength="9223372036854775808"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("integer-overflow", result["rejectedClaims"])
        self.assertIn("file:src-sha256:abc", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})

    def test_repeat_truncated_header(self):
        result = evaluate(payload(declaredLength="32", headerComplete=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("truncated-header", result["rejectedClaims"])
        self.assertIn("file:src-sha256:abc", result["preservedResults"])

    def test_negative_unvalidated_allocation_fails(self):
        result = evaluate(payload(declaredLength="32", allocateUnvalidated=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unvalidated-length-allocation", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("file:src-sha256:abc", result["preservedResults"])
        self.assertFalse(any(item.startswith("allocated:") for item in result["preservedResults"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "declaredLength": "00"},
            {**valid, "maximumBytes": 0},
            {**valid, "headerComplete": "yes"},
            {**valid, "fileToken": " "},
            {key: value for key, value in valid.items() if key != "fileToken"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
