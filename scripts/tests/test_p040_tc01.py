"""TC-P040-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p040_tc01", Path(__file__).resolve().parents[1] / "gates" / "p040_tc01.py"
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
        "code": "minimum",
        "packedBoundary": "aligned",
        "processColor": False,
    }
    base.update(overrides)
    return base


class TcP04001(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P040-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_intervention_expected_and_negative_are_encoded(self):
        self.assertIn("packed sample boundaries", _MODULE.INTERVENTION)
        self.assertIn("declared layout", _MODULE.EXPECTED)
        self.assertIn("contiguous sixteen-bit pixels", _MODULE.NEGATIVE)

    def test_minimum_code_rggb_decodes_declared_layout(self):
        result = evaluate(payload(code="minimum", cfa="RGGB"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"],
            ["4000x3000", "cfa:RGGB", "code:minimum", "padding:0", "parity:even"],
        )

    def test_maximum_code_gbrg_decodes_declared_layout(self):
        result = evaluate(payload(code="maximum", cfa="GBRG", rowPaddingBytes=16))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("code:maximum", result["preservedResults"])
        self.assertIn("cfa:GBRG", result["preservedResults"])
        self.assertIn("padding:16", result["preservedResults"])
        self.assertTrue(any("row padding" in item for item in result["reasons"]))

    def test_odd_crop_is_rejected_before_color(self):
        result = evaluate(payload(cropParity="odd", cfa="BGGR", processColor=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "decoded"})
        self.assertEqual(result["rejectedClaims"], ["odd-crop-parity"])
        self.assertIn("4000x3000", result["preservedResults"])
        self.assertIn("parity:odd", result["preservedResults"])
        self.assertIn("color was not processed", result["openQuestions"])

    def test_grbg_pattern_stays_in_the_decoded_inventory(self):
        result = evaluate(payload(cfa="GRBG", code="mid"))
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("cfa:GRBG", result["preservedResults"])
        self.assertIn("code:mid", result["preservedResults"])

    def test_negative_contiguous_sixteen_bit_pixels_fail(self):
        result = evaluate(
            payload(layout="contiguous_sixteen_bit", processColor=True, code="maximum")
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "decoded"})
        self.assertIn("contiguous-sixteen-bit-pixels", result["rejectedClaims"])
        self.assertIn("color-before-layout-rejection", result["rejectedClaims"])
        self.assertIn("4000x3000", result["preservedResults"])
        self.assertIn("code:maximum", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_perturbed_boundary_rejects_before_color(self):
        result = evaluate(payload(packedBoundary="perturbed", processColor=False))
        self.assertEqual(result["decision"], "layout_rejected")
        self.assertEqual(result["rejectedClaims"], ["perturbed-packed-boundary"])
        self.assertIn("4000x3000", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "cfa"},
            {**valid, "extra": True},
            {**valid, "width": 0},
            {**valid, "cfa": "XXXX"},
            {**valid, "code": "low"},
            {**valid, "cropParity": "odd-ish"},
            {**valid, "processColor": "true"},
            {**valid, "rowPaddingBytes": -1},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
