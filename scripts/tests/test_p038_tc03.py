"""TC-P038-03 oversized records are rejected before allocation."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc03", Path(__file__).resolve().parents[1] / "gates" / "p038_tc03.py"
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
_FILE = "take-fw1.raw"


def payload(**overrides):
    base = {
        "declaredMaxBytes": "4096",
        "payloadLength": "4096",
        "width": "4000",
        "height": "3000",
        "headerTruncated": False,
        "allocateFromLength": False,
        "originalFile": _FILE,
    }
    base.update(overrides)
    return base


class TcP03803(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(result["preservedResults"][0], _FILE)

    def test_declared_maximum_is_bounded_and_keeps_the_file(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "bounded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("declaredMaxBytes:4096", result["preservedResults"])
        self.assertTrue(any("not performed" in item or "original file preserved" in item for item in result["reasons"]))

    def test_maximum_plus_one_is_rejected_without_allocation(self):
        result = evaluate(payload(payloadLength="4097"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("oversize", result["rejectedClaims"])
        self.assertIn("no buffer was allocated", result["openQuestions"])
        self.assertEqual(result["preservedResults"][0], _FILE)

    def test_integer_overflow_boundary_is_rejected(self):
        result = evaluate(
            payload(
                declaredMaxBytes="9223372036854775807",
                payloadLength="9223372036854775808",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("integer-overflow", result["rejectedClaims"])
        self.assertNotIn("oversize", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})

    def test_truncated_header_preserves_the_original(self):
        result = evaluate(payload(headerTruncated=True, payloadLength="128"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["truncated-header"])
        self.assertIn(_FILE, result["preservedResults"])
        self.assertIn("width:4000", result["preservedResults"])

    def test_allocating_from_the_length_field_fails(self):
        result = evaluate(payload(allocateFromLength=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unvalidated-length-allocation", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("no buffer was allocated", result["openQuestions"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "bounded"})

    def test_impossible_dimension_is_rejected(self):
        result = evaluate(payload(width="65536", height="16", payloadLength="16"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("impossible-dimension", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], _FILE)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(payloadLength="04096"))
        with self.assertRaises(ValueError):
            evaluate(None)


if __name__ == "__main__":
    unittest.main()
