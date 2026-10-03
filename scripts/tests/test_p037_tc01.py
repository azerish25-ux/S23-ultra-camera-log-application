"""TC-P037-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p037_tc01", Path(__file__).resolve().parents[1] / "gates" / "p037_tc01.py"
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
        "width": 16,
        "height": 8,
        "stride": 20,
        "packedBits": 10,
        "cfa": "RGGB",
        "cropParity": "even",
        "code": "minimum",
        "contiguous16": False,
        "layoutDeclared": True,
    }
    base.update(overrides)
    return base


class TcP03701(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P037-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_minimum_code_odd_crop_decodes_declared_layout(self):
        result = evaluate(payload(code="minimum", cropParity="odd", cfa="RGGB"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded_layout")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("layout:16x8:RGGB:minimum", result["preservedResults"])
        self.assertIn("crop:odd", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["odd crop retained"])
        self.assertIn("Perturb packed sample boundaries", _MODULE.INTERVENTION)

    def test_maximum_code_with_row_padding_decodes(self):
        result = evaluate(payload(code="maximum", stride=32, cfa="BGGR", cropParity="even"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded_layout")
        self.assertIn("layout:16x8:BGGR:maximum", result["preservedResults"])
        self.assertIn("stride:32", result["preservedResults"])
        self.assertTrue(any("stride padding 12" in item for item in result["reasons"]))

    def test_supported_cfa_patterns_decode(self):
        for cfa in ("RGGB", "BGGR", "GRBG", "GBRG"):
            result = evaluate(payload(cfa=cfa, packedBits=12, stride=24, code="maximum"))
            self.assertEqual(result["decision"], "decoded_layout")
            self.assertIn(f"layout:16x8:{cfa}:maximum", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_contiguous_sixteen_bit_is_rejected_before_color(self):
        result = evaluate(payload(contiguous16=True, code="minimum"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "decoded_layout"})
        self.assertIn("contiguous-sixteen-bit", result["rejectedClaims"])
        self.assertIn("layout:16x8:RGGB:minimum", result["preservedResults"])
        self.assertTrue(any("before color" in item for item in result["reasons"]))
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_odd_width_packing_boundary_is_rejected(self):
        result = evaluate(payload(width=6, stride=20, code="maximum", cropParity="odd"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsupported-packing", result["rejectedClaims"])
        self.assertIn("layout:6x8:RGGB:maximum", result["preservedResults"])
        self.assertIn("crop:odd", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "width"},
            {**valid, "extra": 1},
            {**valid, "width": True},
            {**valid, "cfa": "RGBG"},
            {**valid, "code": "middle"},
            {**valid, "packedBits": 14},
            {**valid, "contiguous16": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
