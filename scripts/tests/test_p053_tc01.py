"""TC-P053-01 negative and bright intermediate values."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc01", Path(__file__).resolve().parents[1] / "gates" / "p053_tc01.py"
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
        "sampleId": "s0",
        "locus": "around-zero",
        "value": "-1",
        "limitKind": "none",
        "limit": "none",
        "implicitClamp": False,
    }
    base.update(overrides)
    return base


class TcP05301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("s0", result["preservedResults"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_around_zero_keeps_a_signed_value(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "preserved")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("value:-1", result["preservedResults"])
        self.assertIn("locus:around-zero", result["preservedResults"])

    def test_source_white_and_over_range_stay_unclamped(self):
        at_white = evaluate(payload(locus="source-white", value="1"))
        self.assertContract(at_white)
        self.assertEqual(at_white["decision"], "preserved")
        self.assertIn("value:1", at_white["preservedResults"])
        over = evaluate(payload(locus="source-white", value="8"))
        self.assertEqual(over["decision"], "preserved")
        self.assertIn("value:8", over["preservedResults"])
        self.assertNotIn(over["decision"], {"qualified", "allowed", "rejected"})

    def test_encoding_boundary_records_an_explicit_limit(self):
        inside = evaluate(
            payload(locus="encoding-boundary", value="1023", limitKind="storage", limit="1023")
        )
        self.assertEqual(inside["decision"], "preserved")
        self.assertIn("value:1023", inside["preservedResults"])
        self.assertIn("limit:storage:1023", inside["preservedResults"])
        beyond = evaluate(
            payload(locus="encoding-boundary", value="1024", limitKind="display", limit="1023")
        )
        self.assertContract(beyond)
        self.assertEqual(beyond["decision"], "bounded")
        self.assertIn("value:1024", beyond["preservedResults"])
        self.assertIn("limit:display:1023", beyond["preservedResults"])
        self.assertNotIn(beyond["decision"], {"qualified", "allowed"})

    def test_implicit_zero_to_one_clamp_is_rejected(self):
        for locus, value in (("around-zero", "-1"), ("source-white", "2"), ("encoding-boundary", "0")):
            result = evaluate(payload(locus=locus, value=value, implicitClamp=True))
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn(f"value:{value}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "preserved"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {key: value for key, value in valid.items() if key != "value"},
            {**valid, "extra": True},
            {**valid, "locus": "black"},
            {**valid, "value": "01"},
            {**valid, "value": "-0"},
            {**valid, "implicitClamp": "true"},
            {**valid, "limitKind": "storage", "limit": "none"},
            {**valid, "limit": "1"},
            {**valid, "sampleId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
