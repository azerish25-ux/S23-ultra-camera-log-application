"""TC-P060-02 eight-bit data in ten-bit storage."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p060_tc02", Path(__file__).resolve().parents[1] / "gates" / "p060_tc02.py"
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
        "spsBitDepth": "10",
        "sourceQuantization": "eight-bit",
        "depthMetadataOnly": False,
        "code": "257",
    }
    base.update(overrides)
    return base


class TcP06002(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P060-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertIn("eight bits", _MODULE.INTERVENTION)
        self.assertIn("metadata", _MODULE.NEGATIVE)

    def test_eight_bit_main10_fails_precision(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "precision_failed")
        self.assertEqual(result["rejectedClaims"], ["eight-bit-quantized"])
        self.assertIn("code:257", result["preservedResults"])
        self.assertIn("stored:256", result["preservedResults"])
        self.assertIn("container:Main10", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_depth_metadata_alone_is_rejected(self):
        result = evaluate(payload(sourceQuantization="ten-bit", depthMetadataOnly=True, code="257"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("bitstream-depth-metadata", result["rejectedClaims"])
        self.assertIn("stored:257", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "precision_failed"})

    def test_repeat_gpu_texture_boundary(self):
        result = evaluate(payload(boundary="gpu-texture", code="1023"))
        self.assertEqual(result["decision"], "precision_failed")
        self.assertIn("boundary:gpu-texture", result["preservedResults"])
        self.assertIn("stored:1020", result["preservedResults"])
        self.assertIn("code:1023", result["preservedResults"])

    def test_repeat_bitmap_and_codec_boundaries(self):
        for boundary, code, stored in (
            ("bitmap-conversion", "5", "4"),
            ("codec-input", "4", "4"),
        ):
            result = evaluate(payload(boundary=boundary, code=code))
            self.assertEqual(result["decision"], "precision_failed")
            self.assertIn(f"boundary:{boundary}", result["preservedResults"])
            self.assertIn(f"stored:{stored}", result["preservedResults"])

    def test_native_ten_bit_is_withheld(self):
        result = evaluate(payload(sourceQuantization="ten-bit", code="257", boundary="codec-input"))
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("stored:257", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {**valid, "code": "1024"},
            {**valid, "code": "08"},
            {**valid, "depthMetadataOnly": "true"},
            {**valid, "boundary": "display"},
            {k: v for k, v in valid.items() if k != "code"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
