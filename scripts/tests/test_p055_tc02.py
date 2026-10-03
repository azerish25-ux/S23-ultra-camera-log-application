"""TC-P055-02 CFA and crop parity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p055_tc02", Path(__file__).resolve().parents[1] / "gates" / "p055_tc02.py"
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
        "sampleX": 0,
        "sampleY": 0,
        "red": "11",
        "green": "22",
        "blue": "33",
        "resetParity": False,
        "site": "interior",
    }
    base.update(overrides)
    return base


class TcP05502(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P055-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_packet_strings(self):
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Resetting mosaic parity after a crop must fail.",
        )
        self.assertIn("odd and even crop origins", _MODULE.INTERVENTION)

    def test_even_origin_keeps_rggb_red(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "parity_kept")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("channel:R", result["preservedResults"])
        self.assertIn("value:R=11", result["preservedResults"])
        self.assertIn("distinct:11,22,33", result["preservedResults"])

    def test_odd_origin_changes_channel_identity(self):
        result = evaluate(payload(cropX=1, cropY=0))
        self.assertEqual(result["decision"], "parity_kept")
        self.assertIn("channel:G", result["preservedResults"])
        self.assertIn("value:G=22", result["preservedResults"])
        self.assertIn("origin:1,0", result["preservedResults"])

    def test_every_mosaic_pattern_is_distinct(self):
        expected = {"RGGB": "R", "BGGR": "B", "GRBG": "G", "GBRG": "G"}
        for pattern, channel in expected.items():
            result = evaluate(payload(pattern=pattern))
            self.assertEqual(result["decision"], "parity_kept")
            self.assertIn(f"channel:{channel}", result["preservedResults"])
            self.assertIn(f"pattern:{pattern}", result["preservedResults"])

    def test_negative_reset_parity_fails_and_keeps_the_channel(self):
        result = evaluate(payload(cropX=1, cropY=1, resetParity=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["mosaic-parity-reset"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("channel:B", result["preservedResults"])
        self.assertIn("value:B=33", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "parity_kept"})

    def test_repeat_border_pixels(self):
        result = evaluate(payload(site="border", sampleX=0, sampleY=0, cropX=0, cropY=1))
        self.assertEqual(result["decision"], "parity_kept")
        self.assertIn("site:border", result["preservedResults"])
        self.assertIn("channel:G", result["preservedResults"])

    def test_repeat_padded_rows(self):
        result = evaluate(payload(site="padded-row", cropY=2, sampleY=1))
        self.assertEqual(result["decision"], "parity_kept")
        self.assertIn("site:padded-row", result["preservedResults"])
        self.assertIn("channel:G", result["preservedResults"])

    def test_repeat_rotated_developed_output(self):
        result = evaluate(payload(site="rotated", cropX=1, pattern="BGGR", resetParity=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("site:rotated", result["preservedResults"])
        self.assertIn("pattern:BGGR", result["preservedResults"])
        self.assertIn("mosaic-parity-reset", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {**valid, "pattern": "XXXX"},
            {**valid, "red": "11", "green": "11"},
            {**valid, "resetParity": 1},
            {**valid, "cropX": -1},
            {**valid, "site": "center"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
