"""TC-P053-02 CFA and crop parity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p053_tc02", Path(__file__).resolve().parents[1] / "gates" / "p053_tc02.py"
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
        "pattern": "RGGB",
        "cropX": 0,
        "cropY": 0,
        "x": 0,
        "y": 0,
        "placement": "interior",
        "resetParity": False,
        "red": 10,
        "green": 20,
        "blue": 30,
    }
    base.update(overrides)
    return base


class TcP05302(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P053-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_even_crop_keeps_rggb_origin(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "channel_identity")
        self.assertIn("channel:R:10", result["preservedResults"])
        self.assertIn("sensor:0,0", result["preservedResults"])
        self.assertIn("interp:0,0", result["preservedResults"])
        self.assertIn("red:10", result["preservedResults"])
        self.assertEqual(result["rejectedClaims"], [])

    def test_odd_crop_shifts_channel_identity(self):
        result = evaluate(payload(cropX=1, cropY=0, pattern="RGGB"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "channel_identity")
        self.assertIn("sensor:1,0", result["preservedResults"])
        self.assertIn("channel:G:20", result["preservedResults"])
        self.assertIn("crop:1,0", result["preservedResults"])

    def test_every_supported_pattern_uses_distinct_channels(self):
        expected = {
            "RGGB": "R:10",
            "GRBG": "G:20",
            "GBRG": "G:20",
            "BGGR": "B:30",
        }
        for pattern, channel in expected.items():
            result = evaluate(payload(pattern=pattern))
            self.assertEqual(result["decision"], "channel_identity")
            self.assertIn("channel:" + channel, result["preservedResults"])
            self.assertIn("blue:30", result["preservedResults"])

    def test_border_pixels_and_padded_rows_keep_coordinates(self):
        border = evaluate(payload(placement="border", x=0, y=0))
        self.assertEqual(border["decision"], "channel_identity")
        self.assertIn("placement:border", border["preservedResults"])
        self.assertIn("interp:0,0", border["preservedResults"])
        padded = evaluate(payload(placement="padded-row", x=1, y=2, cropX=0, cropY=1))
        self.assertEqual(padded["decision"], "channel_identity")
        self.assertIn("placement:padded-row", padded["preservedResults"])
        self.assertIn("sensor:1,3", padded["preservedResults"])

    def test_rotated_output_swaps_interpolation_axes(self):
        result = evaluate(payload(placement="rotated-output", x=1, y=0, cropX=0, cropY=1))
        self.assertEqual(result["decision"], "channel_identity")
        self.assertIn("sensor:0,2", result["preservedResults"])
        self.assertIn("interp:0,2", result["preservedResults"])
        self.assertIn("channel:R:10", result["preservedResults"])

    def test_resetting_parity_after_a_crop_fails(self):
        result = evaluate(payload(cropX=1, cropY=0, resetParity=True, placement="border"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mosaic-parity-reset", result["rejectedClaims"])
        self.assertIn("ignored-phase:0,0", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("sensor:1,0", result["preservedResults"])
        self.assertIn("channel:G:20", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "channel_identity"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "pattern": "YYYY"},
            {**valid, "red": 10, "green": 10, "blue": 30},
            {**valid, "resetParity": 1},
            {**valid, "cropX": -1},
            {**valid, "placement": "rotated"},
            {key: value for key, value in valid.items() if key != "blue"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
