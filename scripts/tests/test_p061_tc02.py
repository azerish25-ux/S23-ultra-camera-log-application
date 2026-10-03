"""TC-P061-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p061_tc02", Path(__file__).resolve().parents[1] / "gates" / "p061_tc02.py"
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
        "containerDepth": 10,
        "imageBits": 8,
        "profileSaysTenBit": True,
        "quantizedToEight": True,
        "code": 940,
    }
    base.update(overrides)
    return base


class TcP06102(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P061-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("eight bits", _MODULE.INTERVENTION)
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Bitstream depth metadata alone must not establish ten-bit image fidelity.",
        )
        self.assertIn("camera input", _MODULE.REPEAT)
        self.assertIn("codec input", _MODULE.REPEAT)

    def test_profile_and_main10_do_not_prove_ten_bit_fidelity(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["eight-bit-in-main10", "precision-not-qualified", "bitstream-depth-not-fidelity"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn("container-depth:10", result["preservedResults"])
        self.assertIn("image-bits:8", result["preservedResults"])
        self.assertIn("code:940", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_ten_bit_samples_are_still_not_qualified(self):
        result = evaluate(payload(imageBits=10, quantizedToEight=False, profileSaysTenBit=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("image-bits:10", result["preservedResults"])
        self.assertTrue(any("not granted" in item for item in result["reasons"]))

    def test_repeat_camera_input(self):
        result = evaluate(payload(boundary="camera-input"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("code:940", result["preservedResults"])

    def test_repeat_gpu_texture(self):
        result = evaluate(payload(boundary="gpu-texture", code=512))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])
        self.assertIn("code:512", result["preservedResults"])
        self.assertIn("bitstream-depth-not-fidelity", result["rejectedClaims"])

    def test_repeat_bitmap_and_codec_boundaries(self):
        for boundary in ("bitmap-conversion", "codec-input"):
            result = evaluate(payload(boundary=boundary))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"boundary:{boundary}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "container": "Main8"},
            {**valid, "containerDepth": 8},
            {**valid, "imageBits": 12},
            {**valid, "profileSaysTenBit": 1},
            {**valid, "code": 1024},
            {**valid, "boundary": "file"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
