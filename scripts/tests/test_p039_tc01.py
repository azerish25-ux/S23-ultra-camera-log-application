"""TC-P039-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p039_tc01", Path(__file__).resolve().parents[1] / "gates" / "p039_tc01.py"
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
        "width": 8,
        "height": 4,
        "stride": 10,
        "packedBits": 10,
        "cfa": "RGGB",
        "cropParity": "even",
        "code": "minimum",
        "contiguous16": False,
        "layoutDeclared": True,
    }
    base.update(overrides)
    return base


class TcP03901(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P039-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_constants_match_the_case(self):
        self.assertIn("packed sample boundaries", _MODULE.INTERVENTION)
        self.assertIn("declared layout", _MODULE.EXPECTED)
        self.assertIn("contiguous sixteen-bit", _MODULE.NEGATIVE)

    def test_minimum_code_decodes_declared_layout(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded_layout")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("layout:8x4:RGGB:minimum", result["preservedResults"])
        self.assertIn("stride:10", result["preservedResults"])
        self.assertIn("crop:even", result["preservedResults"])

    def test_maximum_code_odd_crop_is_decoded_not_qualified(self):
        result = evaluate(
            payload(
                height=9,
                stride=12,
                packedBits=12,
                cfa="BGGR",
                cropParity="odd",
                code="maximum",
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded_layout")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("layout:8x9:BGGR:maximum", result["preservedResults"])
        self.assertIn("crop:odd", result["preservedResults"])
        self.assertEqual(result["openQuestions"], ["odd crop retained"])

    def test_supported_cfa_patterns_keep_dimensions(self):
        for cfa in ("RGGB", "BGGR", "GRBG", "GBRG"):
            result = evaluate(payload(cfa=cfa, code="maximum"))
            self.assertEqual(result["decision"], "decoded_layout")
            self.assertIn(f"layout:8x4:{cfa}:maximum", result["preservedResults"])

    def test_contiguous_sixteen_bit_negative_is_rejected(self):
        result = evaluate(payload(contiguous16=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("contiguous-sixteen-bit", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("layout:8x4:RGGB:minimum", result["preservedResults"])
        self.assertIn("packedBits:10", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        for item in (None, {}, {**valid, "width": 0}, {**valid, "packedBits": 8}):
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
