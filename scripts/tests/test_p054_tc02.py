"""TC-P054-02 CFA and crop parity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p054_tc02", Path(__file__).resolve().parents[1] / "gates" / "p054_tc02.py"
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
        "originX": "0",
        "originY": "0",
        "site": "interior",
        "red": "0.2",
        "green": "0.5",
        "blue": "0.8",
        "parityReset": False,
    }
    base.update(overrides)
    return base


class TcP05402(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P054-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_odd_and_even_origins_keep_channel_identity(self):
        samples = (
            ("RGGB", "0", "0", "R", "0.2"),
            ("RGGB", "1", "0", "G", "0.5"),
            ("BGGR", "0", "1", "G", "0.5"),
            ("GRBG", "1", "1", "G", "0.5"),
            ("GBRG", "1", "0", "B", "0.8"),
        )
        for pattern, origin_x, origin_y, phase, sample in samples:
            result = evaluate(payload(pattern=pattern, originX=origin_x, originY=origin_y))
            self.assertContract(result)
            self.assertEqual(result["decision"], "parity-kept")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(pattern, result["preservedResults"])
            self.assertIn(f"origin:{int(origin_x)},{int(origin_y)}", result["preservedResults"])
            self.assertIn(f"phase:{phase}", result["preservedResults"])
            self.assertIn(f"sample:{sample}", result["preservedResults"])

    def test_repeat_border_pixels_keep_parity(self):
        result = evaluate(payload(pattern="BGGR", originX="3", originY="2", site="border"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("phase:G", result["preservedResults"])
        self.assertIn("site:border", result["preservedResults"])
        self.assertIn("origin:3,2", result["preservedResults"])
        self.assertEqual(_MODULE.channel_at("BGGR", 3, 2), "G")

    def test_repeat_padded_rows_keep_parity(self):
        result = evaluate(payload(pattern="GRBG", originX="2", originY="5", site="padded-row"))
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("phase:B", result["preservedResults"])
        self.assertIn("site:padded-row", result["preservedResults"])
        self.assertIn("sample:0.8", result["preservedResults"])

    def test_repeat_rotated_developed_output_keeps_channel(self):
        result = evaluate(payload(pattern="RGGB", originX="0", originY="1", site="rotated"))
        self.assertEqual(result["decision"], "parity-kept")
        self.assertIn("phase:G", result["preservedResults"])
        self.assertIn("rotated-coordinate:1,0", result["preservedResults"])
        self.assertIn("R:0.2", result["preservedResults"])
        self.assertIn("G:0.5", result["preservedResults"])
        self.assertIn("B:0.8", result["preservedResults"])

    def test_negative_parity_reset_fails_and_keeps_the_correct_phase(self):
        result = evaluate(
            payload(pattern="RGGB", originX="1", originY="1", site="padded-row", parityReset=True)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mosaic-parity-reset"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("phase:B", result["preservedResults"])
        self.assertIn("sample:0.8", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "parity-kept"})

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "pattern"},
            {**valid, "extra": True},
            {**valid, "pattern": "RGBG"},
            {**valid, "originX": "01"},
            {**valid, "originY": -1},
            {**valid, "site": "edge"},
            {**valid, "red": "0.5"},
            {**valid, "green": "0.50"},
            {**valid, "parityReset": "false"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
