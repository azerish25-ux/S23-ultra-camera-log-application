"""TC-P049-01 signed and over-range values are not an implicit zero-to-one clamp."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc01", Path(__file__).resolve().parents[1] / "gates" / "p049_tc01.py"
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
        "code": "40",
        "black": "64",
        "white": "800",
        "storageLimit": "4",
        "locus": "below-black",
        "implicitClamp": False,
    }
    base.update(overrides)
    return base


class TcP04901(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("black:64", result["preservedResults"])
        self.assertIn("white:800", result["preservedResults"])

    def test_constants(self):
        self.assertIn("below black", _MODULE.INTERVENTION)
        self.assertIn("storage or display limit", _MODULE.EXPECTED)
        self.assertIn("zero-to-one clamp", _MODULE.NEGATIVE)

    def test_around_zero_stays_signed_retained(self):
        result = evaluate(payload(code="64", locus="zero"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("norm:0", result["preservedResults"])
        self.assertIn("locus:zero", result["preservedResults"])

    def test_source_white_reference_is_not_scene_white(self):
        result = evaluate(payload(code="800", locus="source-white"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_retained")
        self.assertIn("norm:1", result["preservedResults"])
        self.assertTrue(any("not a universal scene-white boundary" in item for item in result["reasons"]))
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_encoding_boundary_is_held_without_a_unit_clamp(self):
        result = evaluate(payload(code="1536", storageLimit="2", locus="encoding-boundary"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "signed_retained")
        self.assertIn("norm:2", result["preservedResults"])
        self.assertIn("storage-limit:2", result["preservedResults"])
        self.assertTrue(any("storage limit" in item for item in result["reasons"]))

    def test_below_black_and_above_white_keep_the_signed_ratio(self):
        below = evaluate(payload())
        above = evaluate(payload(code="900", locus="above-white"))
        self.assertEqual(below["decision"], "signed_retained")
        self.assertIn("norm:-3/92", below["preservedResults"])
        self.assertEqual(above["decision"], "signed_retained")
        self.assertIn("norm:209/184", above["preservedResults"])
        self.assertNotIn("norm:0", below["preservedResults"])
        self.assertNotIn("norm:1", above["preservedResults"])

    def test_beyond_storage_keeps_the_value_and_records_the_limit(self):
        result = evaluate(payload(code="1536", storageLimit="1", locus="beyond-storage"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "limit_held")
        self.assertIn("norm:2", result["preservedResults"])
        self.assertIn("code:1536", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_implicit_clamp_is_detected_for_both_tails(self):
        for item in (
            payload(implicitClamp=True),
            payload(code="900", locus="above-white", implicitClamp=True),
        ):
            result = evaluate(item)
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("implicit-zero-to-one-clamp", result["rejectedClaims"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "signed_retained"})
            self.assertTrue(any(token.startswith("norm:") and token != "norm:0" and token != "norm:1"
                                for token in result["preservedResults"]))

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "code": "-1"},
            {**valid, "locus": "mid"},
            {**valid, "white": "64"},
            {**valid, "implicitClamp": 1},
            {k: v for k, v in valid.items() if k != "black"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
