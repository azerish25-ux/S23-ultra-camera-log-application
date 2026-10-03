"""TC-P058-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p058_tc02", Path(__file__).resolve().parents[1] / "gates" / "p058_tc02.py"
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
        "container": "Main10",
        "containerBitDepth": 10,
        "profileIndicatesTenBit": True,
        "quantizedBits": 8,
        "boundary": "camera-input",
        "distinctCodes": 256,
    }
    base.update(overrides)
    return base


class TcP05802(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P058-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("Main10", result["preservedResults"])

    def test_negative_depth_metadata_does_not_establish_ten_bit_fidelity(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("eight-bit-quantized", result["rejectedClaims"])
        self.assertIn("metadata-is-not-fidelity", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("profile-ten-bit:true", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("boundary:camera-input", result["preservedResults"])

    def test_ten_bit_codes_are_still_not_qualified(self):
        result = evaluate(payload(quantizedBits=10, distinctCodes=876, boundary="codec-input"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "precision_withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("quantized:10", result["preservedResults"])
        self.assertIn("codes:876", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_gpu_texture_boundary(self):
        result = evaluate(payload(boundary="gpu-texture", quantizedBits=8, distinctCodes=128))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])
        self.assertIn("eight-bit-quantized", result["rejectedClaims"])
        self.assertIn("Main10", result["preservedResults"])

    def test_repeat_bitmap_conversion_boundary(self):
        result = evaluate(payload(boundary="bitmap", quantizedBits=8, profileIndicatesTenBit=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:bitmap", result["preservedResults"])
        self.assertIn("metadata-is-not-fidelity", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_claimed_ten_bit_with_eight_bit_population_fails(self):
        result = evaluate(payload(quantizedBits=10, distinctCodes=256, boundary="codec-input"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("code-population-is-eight-bit", result["rejectedClaims"])
        self.assertIn("metadata-is-not-fidelity", result["rejectedClaims"])
        self.assertNotIn("eight-bit-quantized", result["rejectedClaims"])
        self.assertIn("codes:256", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "boundary"},
            {**valid, "extra": True},
            {**valid, "container": "Main8"},
            {**valid, "containerBitDepth": True},
            {**valid, "quantizedBits": 12},
            {**valid, "boundary": "display"},
            {**valid, "distinctCodes": 0},
            {**valid, "profileIndicatesTenBit": "true"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
