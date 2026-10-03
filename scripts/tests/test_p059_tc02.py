"""TC-P059-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p059_tc02", Path(__file__).resolve().parents[1] / "gates" / "p059_tc02.py"
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
        "boundary": "camera-input",
        "container": "Main10",
        "profile": "Main10",
        "spsBitDepth": 10,
        "quantizedBits": 8,
        "code": 1020,
    }
    base.update(overrides)
    return base


class TcP05902(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P059-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants_encode_the_case(self):
        self.assertIn("eight bits", _MODULE.INTERVENTION)
        self.assertIn("ten-bit container", _MODULE.EXPECTED)
        self.assertIn("Bitstream depth metadata", _MODULE.NEGATIVE)

    def test_negative_sps_depth_does_not_establish_fidelity(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertEqual(result["rejectedClaims"], ["eight-bit-quantized", "metadata-is-not-fidelity"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("sps-bit-depth:10", result["preservedResults"])
        self.assertIn("quantized-bits:8", result["preservedResults"])
        self.assertIn("code:1020", result["preservedResults"])
        self.assertIn("profile:Main10", result["preservedResults"])

    def test_repeat_camera_input_keeps_its_code(self):
        result = evaluate(payload(boundary="camera-input", code=4))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("code:4", result["preservedResults"])
        self.assertNotIn("code:1020", result["preservedResults"])

    def test_repeat_gpu_texture_boundary(self):
        result = evaluate(payload(boundary="gpu-texture", code=256))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])
        self.assertIn("code:256", result["preservedResults"])
        self.assertIn("metadata-is-not-fidelity", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_bitmap_conversion_and_codec_input(self):
        for boundary, code in (("bitmap-conversion", 128), ("codec-input", 512)):
            result = evaluate(payload(boundary=boundary, code=code))
            self.assertEqual(result["decision"], "precision_failed")
            self.assertIn("boundary:" + boundary, result["preservedResults"])
            self.assertIn(f"code:{code}", result["preservedResults"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_ten_bit_samples_are_withheld_rather_than_qualified(self):
        result = evaluate(payload(quantizedBits=10, spsBitDepth=10, code=1023))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_failed"})
        self.assertIn("quantized-bits:10", result["preservedResults"])
        self.assertIn("code:1023", result["preservedResults"])
        self.assertNotIn(_MODULE.NEGATIVE, result["reasons"])

    def test_depth_contradiction_is_rejected(self):
        result = evaluate(payload(quantizedBits=12, spsBitDepth=10))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["depth-contradiction"])
        self.assertIn("quantized-bits:12", result["preservedResults"])
        self.assertIn("sps-bit-depth:10", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "code"},
            {**valid, "extra": 1},
            {**valid, "container": "Main"},
            {**valid, "boundary": "display"},
            {**valid, "spsBitDepth": "10"},
            {**valid, "quantizedBits": 16},
            {**valid, "code": 1024},
            {**valid, "code": -1},
            {**valid, "profile": "main10"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
