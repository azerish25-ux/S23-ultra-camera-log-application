"""TC-P051-01 signed and over-range values are not implicitly clamped."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc01", Path(__file__).resolve().parents[1] / "gates" / "p051_tc01.py"
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
        "samples": [-4, 0, 1, 1023, 1024],
        "blackLevel": 64,
        "whiteLevel": 1023,
        "encodingMin": 0,
        "encodingMax": 4095,
        "clamp": "none",
    }
    base.update(overrides)
    return base


class TcP05101(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("below black", _MODULE.INTERVENTION)
        self.assertIn("over-range", _MODULE.EXPECTED)
        self.assertIn("zero-to-one", _MODULE.NEGATIVE)

    def test_repeat_around_zero(self):
        result = evaluate(payload(samples=[-1, 0, 1]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][:3], ["sample:-1", "sample:0", "sample:1"])

    def test_repeat_source_white_reference(self):
        result = evaluate(payload(samples=[1023, 1024], whiteLevel=1023))
        self.assertContract(result)
        self.assertEqual(result["decision"], "retained")
        self.assertIn("sample:1023", result["preservedResults"])
        self.assertIn("sample:1024", result["preservedResults"])
        self.assertIn("white:1023", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_encoding_boundary(self):
        result = evaluate(
            payload(samples=[4095, 4096, -4], clamp="declared-limit", encodingMax=4095)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "limited")
        self.assertIn("sample:4096", result["preservedResults"])
        self.assertIn("sample:-4", result["preservedResults"])
        self.assertIn("kept:4095", result["preservedResults"])
        self.assertIn("limited:4096->4095", result["preservedResults"])
        self.assertIn("limited:-4->0", result["preservedResults"])
        self.assertIn("encoding:0:4095", result["preservedResults"])

    def test_below_black_and_above_white_stay_signed(self):
        result = evaluate(payload(samples=[-4, 10, 4000], blackLevel=64, whiteLevel=1023))
        self.assertEqual(result["decision"], "retained")
        self.assertIn("sample:-4", result["preservedResults"])
        self.assertIn("sample:4000", result["preservedResults"])
        self.assertIn("black:64", result["preservedResults"])

    def test_implicit_zero_to_one_clamp_is_rejected(self):
        result = evaluate(payload(samples=[-4, 0, 2], clamp="implicit-zero-one"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "retained"})
        self.assertEqual(result["rejectedClaims"], ["implicit-zero-to-one-clamp"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sample:-4", result["preservedResults"])
        self.assertIn("sample:2", result["preservedResults"])
        self.assertIn("white:1023", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "samples": []},
            {**valid, "samples": [1.5]},
            {**valid, "whiteLevel": 64},
            {**valid, "clamp": "clip"},
            {k: v for k, v in valid.items() if k != "blackLevel"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
