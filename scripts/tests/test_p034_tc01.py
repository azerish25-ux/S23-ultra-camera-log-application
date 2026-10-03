"""TC-P034-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p034_tc01", Path(__file__).resolve().parents[1] / "gates" / "p034_tc01.py"
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
        "layout": "RAW10",
        "width": 8,
        "height": 8,
        "rowStride": 10,
        "cropLeft": 1,
        "cropTop": 1,
        "cfa": "RGGB",
        "codeValue": 0,
        "contiguousSixteenBit": False,
    }
    base.update(overrides)
    return base


class TcP03401(unittest.TestCase):
    def assert_contract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P034-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("dim:8x8", result["preservedResults"])

    def test_module_encodes_case_text(self):
        self.assertIn("packed sample boundaries", _MODULE.INTERVENTION)
        self.assertIn("declared layout", _MODULE.EXPECTED)
        self.assertIn("contiguous sixteen-bit", _MODULE.NEGATIVE)
        self.assertEqual(_MODULE.CFAS, ("RGGB", "GRBG", "GBRG", "BGGR"))

    def test_minimum_code_odd_crop_rggb_uses_declared_layout(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "layout_held")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("code:0", result["preservedResults"])
        self.assertIn("cfa:RGGB", result["preservedResults"])
        self.assertIn("crop:1,1", result["preservedResults"])
        self.assertIn("odd-crop-phase", result["openQuestions"])
        self.assertIn("color not processed", result["openQuestions"])

    def test_maximum_code_odd_crop_bggr_uses_declared_layout(self):
        result = evaluate(payload(cfa="BGGR", codeValue=1023, cropLeft=3, cropTop=5))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "layout_held")
        self.assertIn("code:1023", result["preservedResults"])
        self.assertIn("cfa:BGGR", result["preservedResults"])
        self.assertIn("crop:3,5", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_raw12_maximum_and_grbg_keeps_padding(self):
        result = evaluate(
            payload(layout="RAW12", rowStride=16, cfa="GRBG", codeValue=4095, cropLeft=0, cropTop=0)
        )
        self.assertEqual(result["decision"], "layout_held")
        self.assertIn("layout:RAW12", result["preservedResults"])
        self.assertIn("cfa:GRBG", result["preservedResults"])
        self.assertIn("stride:16", result["preservedResults"])
        self.assertNotIn("odd-crop-phase", result["openQuestions"])

    def test_raw16_maximum_gbrg_even_crop(self):
        result = evaluate(
            payload(layout="RAW16", rowStride=16, cfa="GBRG", codeValue=65535, cropLeft=2, cropTop=0)
        )
        self.assertEqual(result["decision"], "layout_held")
        self.assertIn("cfa:GBRG", result["preservedResults"])
        self.assertIn("code:65535", result["preservedResults"])
        self.assertIn("dim:8x8", result["preservedResults"])

    def test_negative_contiguous_sixteen_bit_fails_and_keeps_dimensions(self):
        result = evaluate(
            payload(width=4, height=4, rowStride=8, cropLeft=0, cropTop=0, contiguousSixteenBit=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_held"})
        self.assertIn("contiguous-sixteen-bit", result["rejectedClaims"])
        self.assertIn("dim:4x4", result["preservedResults"])
        self.assertIn("layout:RAW10", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_short_stride_is_rejected_before_color(self):
        result = evaluate(payload(rowStride=9))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("packing-boundary", result["rejectedClaims"])
        self.assertIn("dim:8x8", result["preservedResults"])
        self.assertIn("stride:9", result["preservedResults"])
        self.assertIn("color not processed", result["openQuestions"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(cfa="YYYY"))
        with self.assertRaises(ValueError):
            evaluate(payload(cropLeft=8))


if __name__ == "__main__":
    unittest.main()
