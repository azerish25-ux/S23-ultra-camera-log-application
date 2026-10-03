"""TC-P056-02 mosaic parity survives odd and even crops."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p056_tc02", Path(__file__).resolve().parents[1] / "gates" / "p056_tc02.py"
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
        "originX": 0,
        "originY": 0,
        "channel": "R",
        "resetParity": False,
        "site": "interior",
        "rotation": 0,
    }
    base.update(overrides)
    return base


class TcP05602(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P056-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_even_and_odd_origins_keep_distinct_channels(self):
        even = evaluate(payload())
        odd = evaluate(payload(originX=1, originY=0, channel="G"))
        self.assertContract(even)
        self.assertContract(odd)
        self.assertEqual(even["decision"], "parity-kept")
        self.assertEqual(odd["decision"], "parity-kept")
        self.assertIn("expected:R", even["preservedResults"])
        self.assertIn("expected:G", odd["preservedResults"])
        self.assertIn("origin:1,0", odd["preservedResults"])
        self.assertIn(_MODULE.INTERVENTION, even["reasons"])

    def test_every_pattern_at_an_odd_origin(self):
        expected = {"RGGB": "G", "BGGR": "G", "GRBG": "R", "GBRG": "B"}
        for pattern, channel in expected.items():
            result = evaluate(payload(pattern=pattern, originX=1, originY=2, channel=channel))
            self.assertEqual(result["decision"], "parity-kept")
            self.assertIn(f"pattern:{pattern}", result["preservedResults"])
            self.assertIn(f"expected:{channel}", result["preservedResults"])

    def test_border_pixels_keep_parity(self):
        result = evaluate(payload(site="border", originX=3, originY=0, channel="G"))
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("site:border", result["preservedResults"])
        self.assertIn("expected:G", result["preservedResults"])

    def test_padded_rows_keep_parity(self):
        result = evaluate(payload(site="padded-row", originX=0, originY=1, channel="G"))
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("site:padded-row", result["preservedResults"])
        self.assertEqual(_MODULE.expected_channel("RGGB", 0, 1, 0), "G")

    def test_rotated_developed_output_flips_rggb_corner(self):
        self.assertEqual(_MODULE.expected_channel("RGGB", 0, 0, 180), "B")
        result = evaluate(payload(site="rotated", rotation=180, channel="B"))
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("rotation:180", result["preservedResults"])
        self.assertIn("expected:B", result["preservedResults"])

    def test_negative_parity_reset_fails_and_keeps_the_true_channel(self):
        result = evaluate(payload(originX=1, channel="R", resetParity=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mosaic-parity-reset"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("expected:G", result["preservedResults"])
        self.assertIn("stated:R", result["preservedResults"])
        self.assertIn("origin:1,0", result["preservedResults"])

    def test_channel_mismatch_is_rejected(self):
        result = evaluate(payload(channel="B"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("channel-mismatch", result["rejectedClaims"])
        self.assertIn("expected:R", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "pattern": "RGBG"},
            {**valid, "originX": -1},
            {**valid, "channel": "C"},
            {**valid, "resetParity": 1},
            {**valid, "site": "center"},
            {**valid, "rotation": 45},
            {k: v for k, v in valid.items() if k != "site"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
