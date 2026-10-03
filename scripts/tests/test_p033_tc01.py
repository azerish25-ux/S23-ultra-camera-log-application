"""TC-P033-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p033_tc01", Path(__file__).resolve().parents[1] / "gates" / "p033_tc01.py"
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
        "width": 64,
        "height": 48,
        "cfa": "RGGB",
        "packing": "uint16le-tight",
        "rowPaddingBytes": 0,
        "crop": "full",
        "sampleCode": "mid",
        "assumeContiguous16": False,
        "inventory": ["buffer-a", "dimension-plausible"],
    }
    base.update(overrides)
    return base


class TcP03301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P033-01")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_repeat_minimum_code_uses_declared_layout(self):
        result = evaluate(payload(sampleCode="min"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_declared")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("code:min", result["preservedResults"])
        self.assertIn("64x48", result["preservedResults"])
        self.assertIn("buffer-a", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertEqual(_MODULE.INTERVENTION[:7], "Perturb")

    def test_repeat_maximum_code_uses_declared_layout(self):
        result = evaluate(payload(sampleCode="max", cfa="GRBG"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_declared")
        self.assertNotIn(result["decision"], _FORBIDDEN)
        self.assertIn("code:max", result["preservedResults"])
        self.assertIn("cfa:GRBG", result["preservedResults"])
        self.assertIn("dimension-plausible", result["preservedResults"])

    def test_repeat_odd_crop_rejects_before_color(self):
        result = evaluate(payload(crop="1,0,62,48"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-layout", result["rejectedClaims"])
        self.assertNotIn("contiguous-sixteen-bit", result["rejectedClaims"])
        self.assertIn("crop:1,0,62,48", result["preservedResults"])
        self.assertIn("64x48", result["preservedResults"])
        self.assertIn("buffer-a", result["preservedResults"])
        self.assertTrue(any("odd-crop" in item for item in result["reasons"]))
        self.assertTrue(any("before processing color" in item for item in result["reasons"]))
        self.assertEqual(result["openQuestions"], ["color processing was not started"])

    def test_repeat_all_supported_cfa_patterns(self):
        for cfa in ("RGGB", "GRBG", "GBRG", "BGGR"):
            result = evaluate(payload(cfa=cfa, sampleCode="min"))
            self.assertEqual(result["decision"], "layout_declared")
            self.assertNotIn(result["decision"], _FORBIDDEN)
            self.assertIn("cfa:" + cfa, result["preservedResults"])
            self.assertIn("code:min", result["preservedResults"])

    def test_negative_contiguous_sixteen_bit_fails(self):
        tight = evaluate(payload(assumeContiguous16=True, sampleCode="max"))
        packed = evaluate(payload(assumeContiguous16=True, packing="packed10"))
        for result in (tight, packed):
            self.assertContract(result)
            self.assertEqual(result["decision"], "rejected")
            self.assertNotIn(result["decision"], _FORBIDDEN)
            self.assertIn("contiguous-sixteen-bit", result["rejectedClaims"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertIn("64x48", result["preservedResults"])
            self.assertIn("buffer-a", result["preservedResults"])
        self.assertEqual(tight["rejectedClaims"], ["contiguous-sixteen-bit"])
        self.assertIn("unsupported-layout", packed["rejectedClaims"])

    def test_declared_padding_is_not_treated_as_contiguous(self):
        result = evaluate(payload(packing="uint16le-padded", rowPaddingBytes=8, sampleCode="min"))
        self.assertEqual(result["decision"], "layout_declared")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("packing:uint16le-padded", result["preservedResults"])
        self.assertIn("padding:8", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_packed10_rejects_before_color_and_keeps_dimensions(self):
        result = evaluate(payload(packing="packed10", sampleCode="max"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unsupported-layout"])
        self.assertIn("packing:packed10", result["preservedResults"])
        self.assertIn("code:max", result["preservedResults"])
        self.assertIn("dimension-plausible", result["preservedResults"])
        self.assertNotIn(result["decision"], _FORBIDDEN)

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "crop"},
            {**valid, "extra": True},
            {**valid, "width": True},
            {**valid, "width": 0},
            {**valid, "cfa": "RGBG"},
            {**valid, "packing": "uint8"},
            {**valid, "sampleCode": "min-max"},
            {**valid, "crop": "1,0"},
            {**valid, "crop": "01,0,62,48"},
            {**valid, "assumeContiguous16": 1},
            {**valid, "inventory": []},
            {**valid, "inventory": ["buffer-a", "buffer-a"]},
            {**valid, "rowPaddingBytes": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
