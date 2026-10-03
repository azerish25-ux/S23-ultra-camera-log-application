"""TC-P062-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p062_tc02", Path(__file__).resolve().parents[1] / "gates" / "p062_tc02.py"
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
        "sampleId": "ramp-mid",
        "boundary": "codec-input",
        "code": 513,
        "quantizedToEight": True,
        "numericComparison": False,
        "container": "Main10",
        "profile": "Main10",
        "depthMetadata": "10",
    }
    base.update(overrides)
    return base


class TcP06202(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P062-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Bitstream depth metadata alone must not establish ten-bit image fidelity.",
        )

    def test_eight_bit_quantization_fails_precision(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertEqual(result["rejectedClaims"], ["eight-bit-before-pack", "metadata-not-fidelity"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source:513", result["preservedResults"])
        self.assertIn("stored:512", result["preservedResults"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn("profile:Main10", result["preservedResults"])
        self.assertIn("depth-metadata:10", result["preservedResults"])
        self.assertIn("precision-qualified:no", result["preservedResults"])
        self.assertIn("ramp-mid", result["preservedResults"])

    def test_metadata_alone_is_not_ten_bit_fidelity(self):
        result = evaluate(payload(quantizedToEight=False, code=640))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["metadata-not-fidelity"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("source:640", result["preservedResults"])
        self.assertIn("stored:640", result["preservedResults"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_failed"})

    def test_repeat_camera_input_and_gpu_texture(self):
        for boundary in ("camera-input", "gpu-texture"):
            result = evaluate(payload(boundary=boundary, sampleId=boundary))
            self.assertEqual(result["decision"], "precision_failed")
            self.assertIn(f"boundary:{boundary}", result["preservedResults"])
            self.assertIn(boundary, result["preservedResults"])
            self.assertIn("stored:512", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_repeat_bitmap_conversion_and_codec_input(self):
        for boundary in ("bitmap-conversion", "codec-input"):
            result = evaluate(payload(boundary=boundary))
            self.assertEqual(result["decision"], "precision_failed")
            self.assertIn(f"boundary:{boundary}", result["preservedResults"])

    def test_numeric_comparison_still_does_not_qualify(self):
        result = evaluate(payload(quantizedToEight=False, numericComparison=True, code=1000))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:1000", result["preservedResults"])
        self.assertIn("precision-qualified:no", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "code"},
            {**valid, "extra": True},
            {**valid, "code": True},
            {**valid, "code": 1024},
            {**valid, "boundary": "display"},
            {**valid, "container": "Main"},
            {**valid, "quantizedToEight": "true"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
