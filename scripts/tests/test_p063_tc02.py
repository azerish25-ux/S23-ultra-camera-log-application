"""TC-P063-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p063_tc02", Path(__file__).resolve().parents[1] / "gates" / "p063_tc02.py"
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
        "sampleId": "ramp",
        "boundary": "codec-input",
        "container": "Main10",
        "profile": "Main10",
        "bitstreamDepth": "10",
        "quantizedToEight": True,
    }
    base.update(overrides)
    return base


class TcP06302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P063-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Quantize the source or intermediate to eight bits before packing into a Main10 output.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Bitstream depth metadata alone must not establish ten-bit image fidelity.",
        )

    def test_bitstream_depth_does_not_establish_fidelity(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertEqual(
            result["rejectedClaims"],
            ["eight-bit-quantized", "bitstream-depth-not-fidelity"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("bitstream-depth:10", result["preservedResults"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn("profile:Main10", result["preservedResults"])
        self.assertIn("ramp", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_camera_input(self):
        result = evaluate(payload(sampleId="sensor", boundary="camera-input"))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("bitstream-depth:10", result["preservedResults"])

    def test_repeat_gpu_texture(self):
        result = evaluate(payload(sampleId="gpu", boundary="gpu-texture"))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])

    def test_repeat_bitmap_conversion(self):
        result = evaluate(payload(sampleId="bitmap", boundary="bitmap-conversion"))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:bitmap-conversion", result["preservedResults"])
        self.assertIn("container:Main10", result["preservedResults"])

    def test_native_ten_bit_is_withheld(self):
        result = evaluate(payload(quantizedToEight=False, boundary="codec-input"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("bitstream-depth:10", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_failed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {k: v for k, v in valid.items() if k != "boundary"},
            {**valid, "boundary": "display"},
            {**valid, "bitstreamDepth": "12"},
            {**valid, "quantizedToEight": 1},
            {**valid, "container": "P010"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
