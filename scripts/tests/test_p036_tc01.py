"""TC-P036-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p036_tc01", Path(__file__).resolve().parents[1] / "gates" / "p036_tc01.py"
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
        "width": 4000,
        "height": 3000,
        "layout": "declared_packed",
        "rowPaddingBytes": 0,
        "cropParity": "even",
        "cfa": "RGGB",
        "code": "mid",
        "packedBoundary": "aligned",
        "processColor": False,
    }
    base.update(overrides)
    return base


class TcP03601(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P036-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_minimum_code_uses_declared_layout(self):
        result = evaluate(payload(code="minimum", rowPaddingBytes=16))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertEqual(result["preservedResults"][0], "4000x3000")
        self.assertIn("code:minimum", result["preservedResults"])
        self.assertIn("padding:16", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_maximum_code_uses_declared_layout(self):
        result = evaluate(payload(code="maximum", cfa="BGGR", width=1920, height=1080))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("1920x1080", result["preservedResults"])
        self.assertIn("code:maximum", result["preservedResults"])
        self.assertIn("cfa:BGGR", result["preservedResults"])

    def test_odd_crop_rejects_before_color(self):
        result = evaluate(payload(cropParity="odd", processColor=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "decoded"})
        self.assertIn("odd-crop-parity", result["rejectedClaims"])
        self.assertIn("4000x3000", result["preservedResults"])
        self.assertIn("color was not processed", result["openQuestions"])
        self.assertNotIn("color-before-layout-rejection", result["rejectedClaims"])

    def test_all_supported_cfa_patterns_decode(self):
        for cfa in ("RGGB", "BGGR", "GRBG", "GBRG"):
            result = evaluate(payload(cfa=cfa))
            self.assertEqual(result["decision"], "decoded")
            self.assertIn(f"cfa:{cfa}", result["preservedResults"])
            self.assertIn("4000x3000", result["preservedResults"])

    def test_perturbed_boundary_rejects_before_color_and_keeps_size(self):
        result = evaluate(payload(packedBoundary="perturbed"))
        self.assertEqual(result["decision"], "layout_rejected")
        self.assertIn("perturbed-packed-boundary", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][0], "4000x3000")

    def test_negative_contiguous_sixteen_bit_fails(self):
        result = evaluate(payload(layout="contiguous_sixteen_bit", processColor=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "decoded"})
        self.assertIn("contiguous-sixteen-bit-pixels", result["rejectedClaims"])
        self.assertIn("4000x3000", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_color_before_rejection_fails(self):
        result = evaluate(payload(cropParity="odd", processColor=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("color-before-layout-rejection", result["rejectedClaims"])
        self.assertIn("parity:odd", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "width": 0},
            {**valid, "layout": "raw16"},
            {**valid, "cfa": "XXXX"},
            {**valid, "processColor": 1},
            {**valid, "rowPaddingBytes": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
