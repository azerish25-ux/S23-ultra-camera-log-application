"""TC-P049-02 mosaic parity stays on sensor coordinates after a crop."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p049_tc02", Path(__file__).resolve().parents[1] / "gates" / "p049_tc02.py"
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
        "cfa": "RGGB",
        "cropLeft": 1,
        "cropTop": 0,
        "x": 1,
        "y": 0,
        "site": "interior",
        "resetParityAfterCrop": False,
    }
    base.update(overrides)
    return base


class TcP04902(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P049-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertIn("mosaic pattern", _MODULE.INTERVENTION)
        self.assertIn("channel identity", _MODULE.EXPECTED)
        self.assertIn("mosaic parity", _MODULE.NEGATIVE)

    def test_every_cfa_keeps_distinct_sensor_channels(self):
        pixels = {(0, 0), (1, 0), (0, 1), (1, 1)}
        for cfa in ("RGGB", "GRBG", "GBRG", "BGGR"):
            channels = set()
            for x, y in pixels:
                result = evaluate(payload(cfa=cfa, cropLeft=0, cropTop=0, x=x, y=y))
                self.assertEqual(result["decision"], "channel_held")
                channel = next(item for item in result["preservedResults"] if item.startswith("channel:"))
                channels.add(channel)
                self.assertIn(f"interp:{x},{y}", result["preservedResults"])
            self.assertEqual(channels, {"channel:R", "channel:G", "channel:B"})

    def test_odd_crop_is_green_not_a_reset_red(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "channel_held")
        self.assertIn("channel:G", result["preservedResults"])
        self.assertIn("interp:1,0", result["preservedResults"])
        self.assertNotIn("channel:R", result["preservedResults"])

    def test_even_crop_still_rejects_a_parity_reset(self):
        result = evaluate(
            payload(cropLeft=2, cropTop=2, x=2, y=2, resetParityAfterCrop=True)
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mosaic-parity-reset", result["rejectedClaims"])
        self.assertIn("channel:R", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "channel_held"})

    def test_odd_reset_records_the_disagreement_and_keeps_the_sensor_channel(self):
        result = evaluate(payload(resetParityAfterCrop=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["mosaic-parity-reset", "channel-disagreement:R"],
        )
        self.assertIn("channel:G", result["preservedResults"])
        self.assertIn("cfa:RGGB", result["preservedResults"])

    def test_border_pixels_keep_the_sensor_channel(self):
        result = evaluate(payload(cropLeft=0, cropTop=0, x=0, y=0, site="border"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "channel_held")
        self.assertIn("site:border", result["preservedResults"])
        self.assertIn("channel:R", result["preservedResults"])

    def test_padded_rows_and_rotated_output_do_not_change_phase(self):
        padded = evaluate(payload(cropLeft=0, cropTop=2, x=1, y=4, site="padded-row"))
        rotated = evaluate(payload(cropLeft=0, cropTop=2, x=1, y=4, site="rotated"))
        self.assertEqual(padded["decision"], "channel_held")
        self.assertEqual(rotated["decision"], "channel_held")
        self.assertIn("channel:G", padded["preservedResults"])
        self.assertIn("channel:G", rotated["preservedResults"])
        self.assertIn("site:padded-row", padded["preservedResults"])
        self.assertIn("site:rotated", rotated["preservedResults"])
        self.assertIn("interp:1,4", rotated["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cfa": "RGBG"},
            {**valid, "x": 0},
            {**valid, "site": "seam"},
            {**valid, "cropLeft": True},
            {k: v for k, v in valid.items() if k != "y"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
