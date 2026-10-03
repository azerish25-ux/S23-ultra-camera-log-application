"""TC-P064-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p064_tc02", Path(__file__).resolve().parents[1] / "gates" / "p064_tc02.py"
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
        "boundary": "codec-input",
        "quantizedToEight": False,
        "container": "Main10",
        "containerBitDepth": 10,
        "profileIndicatesTenBit": True,
        "bitstreamDepthMetadata": 10,
        "usefulPrecisionEvidence": True,
    }
    base.update(overrides)
    return base


class TcP06402(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P064-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Bitstream depth metadata alone must not establish ten-bit image fidelity.",
        )
        self.assertIn("camera input", _MODULE.REPEAT)
        self.assertIn("codec input", _MODULE.REPEAT)

    def test_useful_precision_is_withheld_not_qualified(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertIn("profile-ten-bit:true", result["preservedResults"])

    def test_eight_bit_quantization_fails_despite_main10(self):
        result = evaluate(payload(quantizedToEight=True, usefulPrecisionEvidence=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("eight-bit-before-main10", result["rejectedClaims"])
        self.assertIn("bitstream-depth-not-fidelity", result["rejectedClaims"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn("profile-ten-bit:true", result["preservedResults"])
        self.assertIn("quantized-eight:true", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_bitstream_metadata_alone_is_not_fidelity(self):
        result = evaluate(payload(usefulPrecisionEvidence=False, quantizedToEight=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["bitstream-depth-not-fidelity"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("bitstream-depth:10", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_camera_input_boundary(self):
        result = evaluate(payload(boundary="camera-input", quantizedToEight=True, usefulPrecisionEvidence=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("eight-bit-before-main10", result["rejectedClaims"])
        self.assertIn("container:Main10", result["preservedResults"])

    def test_repeat_gpu_texture_boundary(self):
        result = evaluate(payload(boundary="gpu-texture", usefulPrecisionEvidence=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])
        self.assertIn("bitstream-depth-not-fidelity", result["rejectedClaims"])

    def test_repeat_bitmap_conversion_boundary(self):
        result = evaluate(payload(boundary="bitmap-conversion"))
        self.assertEqual(result["decision"], "withheld")
        self.assertIn("boundary:bitmap-conversion", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "container": "Main"},
            {**valid, "boundary": "file"},
            {**valid, "containerBitDepth": True},
            {**valid, "quantizedToEight": 1},
            {**valid, "bitstreamDepthMetadata": 12},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
