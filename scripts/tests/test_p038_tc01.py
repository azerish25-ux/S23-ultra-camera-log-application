"""TC-P038-01 packing boundaries are not contiguous sixteen-bit pixels."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p038_tc01", Path(__file__).resolve().parents[1] / "gates" / "p038_tc01.py"
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
        "width": 64,
        "height": 48,
        "rowPadding": 16,
        "cropLeft": 2,
        "cropTop": 2,
        "cropWidth": 32,
        "cropHeight": 24,
        "cfa": "RGGB",
        "packing": "packed10",
        "sampleCode": "min",
        "treatAsContiguous16": False,
    }
    base.update(overrides)
    return base


class TcP03801(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P038-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("dimensions:64x48", result["preservedResults"])

    def test_constants(self):
        self.assertIn("crop parity", _MODULE.INTERVENTION)
        self.assertIn("before processing color", _MODULE.EXPECTED)
        self.assertIn("contiguous sixteen-bit", _MODULE.NEGATIVE)

    def test_minimum_code_uses_declared_layout(self):
        result = evaluate(payload(sampleCode="min"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_accepted")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("code:min", result["preservedResults"])
        self.assertIn("padding:16", result["preservedResults"])
        self.assertIn("cfa:RGGB", result["preservedResults"])
        self.assertTrue(any("declared layout" in item for item in result["reasons"]))
        self.assertTrue(any("color was not processed" in item for item in result["reasons"]))

    def test_maximum_code_keeps_the_same_layout_decision(self):
        result = evaluate(payload(sampleCode="max", packing="packed12", cfa="GRBG"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "layout_accepted")
        self.assertIn("code:max", result["preservedResults"])
        self.assertIn("packing:packed12", result["preservedResults"])
        self.assertIn("cfa:GRBG", result["preservedResults"])

    def test_all_supported_cfa_patterns_are_declared_layouts(self):
        for cfa in ("RGGB", "GRBG", "GBRG", "BGGR"):
            result = evaluate(payload(cfa=cfa, packing="unpacked16", rowPadding=0))
            self.assertEqual(result["decision"], "layout_accepted")
            self.assertIn(f"cfa:{cfa}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_odd_crop_is_rejected_before_color(self):
        result = evaluate(payload(cropLeft=1, cropTop=3))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["unsupported-layout"])
        self.assertIn("crop:32x24+1+3", result["preservedResults"])
        self.assertIn("dimensions:64x48", result["preservedResults"])
        self.assertIn("color processing not started", result["openQuestions"])
        self.assertTrue(any("before processing color" in item for item in result["reasons"]))

    def test_contiguous_sixteen_bit_assumption_fails(self):
        for packing, padding in (("packed10", 16), ("unpacked16", 0)):
            result = evaluate(
                payload(packing=packing, rowPadding=padding, treatAsContiguous16=True)
            )
            self.assertEqual(result["decision"], "rejected")
            self.assertIn("contiguous-sixteen-bit", result["rejectedClaims"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "layout_accepted"})
            self.assertIn(f"packing:{packing}", result["preservedResults"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "width": 63},
            {**valid, "cfa": "RGBG"},
            {**valid, "packing": "raw16"},
            {**valid, "sampleCode": "mid"},
            {**valid, "treatAsContiguous16": 1},
            {k: v for k, v in valid.items() if k != "rowPadding"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
