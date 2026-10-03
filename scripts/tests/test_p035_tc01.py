"""TC-P035-01 packing boundary corruption."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p035_tc01", Path(__file__).resolve().parents[1] / "gates" / "p035_tc01.py"
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
        "format": "RAW10",
        "width": 4,
        "height": 4,
        "rowStride": 8,
        "cropLeft": 1,
        "cropTop": 1,
        "cfa": "RGGB",
        "sample": "alternating",
        "perturbation": "none",
        "reader": "declared",
    }
    base.update(overrides)
    return base


class TcP03501(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P035-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_repeat_minimum_codes(self):
        result = evaluate(payload(sample="minimum", format="RAW10"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("code:0", result["preservedResults"])
        self.assertNotIn("code:1023", result["preservedResults"])
        self.assertIn("format:RAW10", result["preservedResults"])
        self.assertIn("crop:1,1", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_repeat_maximum_codes(self):
        result = evaluate(payload(sample="maximum", format="RAW12", rowStride=8))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("code:4095", result["preservedResults"])
        self.assertNotIn("code:0", result["preservedResults"])
        self.assertIn("format:RAW12", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_odd_crop_keeps_rggb_phase(self):
        result = evaluate(payload(format="RAW_SENSOR", rowStride=12, cfa="RGGB"))
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("cfa-at:1,1=B", result["preservedResults"])
        self.assertNotIn("cfa-at:1,1=R", result["preservedResults"])
        self.assertIn("size:4x4", result["preservedResults"])

    def test_repeat_cfa_pattern_bggr(self):
        result = evaluate(payload(cfa="BGGR", format="RAW_SENSOR", rowStride=12, sample="minimum"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "decoded")
        self.assertIn("cfa-at:1,1=R", result["preservedResults"])
        self.assertIn("cfa:BGGR", result["preservedResults"])
        self.assertIn("code:0", result["preservedResults"])

    def test_negative_contiguous_uint16_fails(self):
        result = evaluate(payload(reader="contiguous_u16", sample="maximum", format="RAW10"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["contiguous-sixteen-bit-pixels"])
        self.assertIn("format:RAW10", result["preservedResults"])
        self.assertIn("crop:1,1", result["preservedResults"])
        self.assertIn("sample:maximum", result["preservedResults"])
        self.assertFalse(any(item.startswith("cfa-at:") for item in result["preservedResults"]))
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_packed_boundary_and_padding_reject_before_color(self):
        boundary = evaluate(payload(width=6, height=2, perturbation="packed_boundary", rowStride=4))
        self.assertEqual(boundary["decision"], "rejected")
        self.assertIn("unsupported-packing-boundary", boundary["rejectedClaims"])
        self.assertIn("size:6x2", boundary["preservedResults"])
        self.assertFalse(any(item.startswith("cfa-at:") for item in boundary["preservedResults"]))
        padding = evaluate(payload(perturbation="row_padding", rowStride=5))
        self.assertEqual(padding["decision"], "rejected")
        self.assertIn("unsupported-row-padding", padding["rejectedClaims"])
        self.assertIn("stride:5", padding["preservedResults"])
        parity = evaluate(payload(perturbation="crop_parity", cropLeft=0, cropTop=1))
        self.assertEqual(parity["decision"], "rejected")
        self.assertIn("unsupported-crop-parity", parity["rejectedClaims"])
        self.assertIn("crop:0,1", parity["preservedResults"])
        self.assertNotIn(parity["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {key: value for key, value in valid.items() if key != "reader"},
            {**valid, "extra": True},
            {**valid, "width": 6},
            {**valid, "cropLeft": 0},
            {**valid, "perturbation": "crop_parity"},
            {**valid, "sample": "other"},
            {**valid, "rowStride": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
