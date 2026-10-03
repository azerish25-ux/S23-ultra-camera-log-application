"""TC-P057-02 eight-bit samples do not become ten-bit fidelity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p057_tc02", Path(__file__).resolve().parents[1] / "gates" / "p057_tc02.py"
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
        "sourceBits": 8,
        "containerBits": 10,
        "profileIndicatesTenBit": True,
        "quantizedBeforePack": True,
    }
    base.update(overrides)
    return base


class TcP05702(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P057-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_camera_input_eight_bit_pack_is_rejected(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["eight-bit-in-ten-bit-container", "depth-metadata-not-fidelity"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("boundary:camera-input", result["preservedResults"])
        self.assertIn("source-bits:8", result["preservedResults"])
        self.assertIn("container-bits:10", result["preservedResults"])

    def test_repeat_at_codec_input(self):
        result = evaluate(payload(boundary="codec-input", sourceBits=10, quantizedBeforePack=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("boundary:codec-input", result["preservedResults"])
        self.assertIn("depth-metadata-not-fidelity", result["rejectedClaims"])
        self.assertIn("source-bits:10", result["preservedResults"])

    def test_repeat_at_gpu_texture_and_bitmap(self):
        for boundary in ("gpu-texture", "bitmap-conversion"):
            result = evaluate(payload(boundary=boundary, quantizedBeforePack=False))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"boundary:{boundary}", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed", "withheld"})

    def test_true_ten_bit_path_is_not_a_precision_qualification(self):
        result = evaluate(
            payload(boundary="codec-input", sourceBits=10, quantizedBeforePack=False)
        )
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source-bits:10", result["preservedResults"])
        self.assertTrue(any("not promoted" in item for item in result["reasons"]))

    def test_profile_flag_without_early_quantize_stays_withheld(self):
        result = evaluate(payload(sourceBits=10, quantizedBeforePack=False, profileIndicatesTenBit=True))
        self.assertEqual(result["decision"], "withheld")
        self.assertNotIn("depth-metadata-not-fidelity", result["rejectedClaims"])

    def test_eight_bit_container_is_rejected(self):
        result = evaluate(payload(containerBits=8, sourceBits=8, profileIndicatesTenBit=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["container-not-main10"])
        self.assertIn("container-bits:8", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "sourceBits": True},
            {**valid, "sourceBits": 12},
            {**valid, "boundary": "display"},
            {**valid, "quantizedBeforePack": 1},
            {k: v for k, v in valid.items() if k != "boundary"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
