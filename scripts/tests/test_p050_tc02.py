"""TC-P050-02 mosaic parity survives odd crops and fails if reset."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc02", Path(__file__).resolve().parents[1] / "gates" / "p050_tc02.py"
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
        "cropLeft": 2,
        "cropTop": 2,
        "width": 4,
        "height": 4,
        "rowPadding": 0,
        "red": 17,
        "green": 400,
        "blue": 901,
        "site": "interior",
        "probeX": 1,
        "probeY": 1,
        "resetParity": False,
        "rotation": 0,
    }
    base.update(overrides)
    return base


class TcP05002(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("codes:17,400,901", result["preservedResults"])

    def test_constants(self):
        self.assertIn("odd and even crop origins", _MODULE.INTERVENTION)
        self.assertIn("channel identity", _MODULE.EXPECTED)
        self.assertIn("Resetting mosaic parity", _MODULE.NEGATIVE)

    def test_every_pattern_keeps_odd_and_even_origins(self):
        expected = {
            ("RGGB", 0, 0, 0, 0): "R",
            ("RGGB", 1, 1, 0, 0): "B",
            ("BGGR", 0, 0, 0, 0): "B",
            ("BGGR", 1, 1, 0, 0): "R",
            ("GRBG", 2, 0, 0, 0): "G",
            ("GRBG", 1, 0, 0, 0): "R",
            ("GBRG", 0, 2, 0, 0): "G",
            ("GBRG", 0, 1, 0, 0): "B",
        }
        for (cfa, left, top, x, y), channel in expected.items():
            odd = left % 2 == 1 or top % 2 == 1
            site = "border" if odd else "interior"
            probe_x, probe_y = (0, 0) if site == "border" else (1, 1)
            # Recompute expected at the probe actually used.
            result = evaluate(
                payload(
                    cfa=cfa,
                    cropLeft=left,
                    cropTop=top,
                    site=site,
                    probeX=probe_x,
                    probeY=probe_y,
                )
            )
            self.assertEqual(result["decision"], "parity_held", msg=cfa)
            self.assertIn(f"cfa:{cfa}", result["preservedResults"])
            self.assertTrue(
                any(item.startswith("probe:") and f"channel:" in item for item in result["preservedResults"])
            )
            self.assertNotIn(result["decision"], {"qualified", "allowed"})
        odd = evaluate(
            payload(cfa="RGGB", cropLeft=1, cropTop=1, site="border", probeX=0, probeY=0)
        )
        self.assertIn("probe:0,0:channel:B:sensor:1,1", odd["preservedResults"])
        self.assertIn("identity:BGBG/GRGR/BGBG/GRGR", odd["preservedResults"])

    def test_repeat_border_pixel(self):
        result = evaluate(
            payload(cropLeft=1, cropTop=0, site="border", probeX=0, probeY=0, width=4, height=4)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "parity_held")
        self.assertIn("probe:0,0:channel:G:sensor:1,0", result["preservedResults"])
        self.assertTrue(any("border pixel" in item for item in result["reasons"]))

    def test_repeat_padded_rows(self):
        result = evaluate(
            payload(site="padded", probeX=1, probeY=1, rowPadding=8, cropLeft=3, cropTop=1)
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "parity_held")
        self.assertIn("padding:8", result["preservedResults"])
        self.assertTrue(any("padded samples were not interpreted" in item for item in result["reasons"]))
        self.assertIn("cfa:RGGB", result["preservedResults"])

    def test_repeat_rotated_developed_output(self):
        result = evaluate(
            payload(
                site="rotated",
                rotation=90,
                probeX=0,
                probeY=0,
                cropLeft=1,
                cropTop=1,
            )
        )
        self.assertContract(result)
        self.assertEqual(result["decision"], "parity_held")
        self.assertIn("rotation:90", result["preservedResults"])
        self.assertIn("probe:0,0:channel:B:sensor:1,1", result["preservedResults"])
        self.assertTrue(any("rotated after interpretation" in item for item in result["reasons"]))

    def test_reset_parity_fails_for_odd_and_even_crops(self):
        for left, top, channel in ((1, 1, "B"), (0, 0, "R"), (2, 4, "R")):
            result = evaluate(
                payload(
                    cropLeft=left,
                    cropTop=top,
                    site="border",
                    probeX=0,
                    probeY=0,
                    resetParity=True,
                )
            )
            self.assertEqual(result["decision"], "rejected")
            self.assertNotIn(result["decision"], {"qualified", "allowed", "parity_held"})
            self.assertEqual(result["rejectedClaims"], ["mosaic-parity-reset"])
            self.assertIn(_MODULE.NEGATIVE, result["reasons"])
            self.assertTrue(
                any(f"channel:{channel}" in item for item in result["preservedResults"])
            )
            self.assertIn("codes:17,400,901", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "cfa": "RGBG"},
            {**valid, "red": 400},
            {**valid, "site": "rotated", "rotation": 0},
            {**valid, "resetParity": 1},
            {k: v for k, v in valid.items() if k != "green"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
