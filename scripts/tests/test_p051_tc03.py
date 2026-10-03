"""TC-P051-03 borders omit missing rows and reject stale or halo failures."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p051_tc03", Path(__file__).resolve().parents[1] / "gates" / "p051_tc03.py"
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
        "site": "corner-nw",
        "impulse": 12,
        "readOutside": False,
        "ignoreHalo": False,
        "staleSlot": False,
    }
    base.update(overrides)
    return base


class TcP05103(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P051-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_constants(self):
        self.assertIn("tile seam", _MODULE.INTERVENTION)
        self.assertIn("stale reads", _MODULE.EXPECTED)
        self.assertIn("required halos", _MODULE.NEGATIVE)

    def test_repeat_four_corners(self):
        expected = {
            "corner-nw": "0,6,0",
            "corner-ne": "0,12,0",
            "corner-sw": "0,12,0",
            "corner-se": "0,4,0",
        }
        for site, border in expected.items():
            result = evaluate(payload(site=site, impulse=12))
            self.assertContract(result)
            self.assertEqual(result["decision"], "border_applied")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"border:{site}:{border}", result["preservedResults"])
            self.assertIn("impulse:12", result["preservedResults"])

    def test_repeat_kernel_support_boundary(self):
        north = evaluate(payload(site="kernel-north"))
        south = evaluate(payload(site="kernel-south"))
        self.assertEqual(north["decision"], "border_applied")
        self.assertEqual(south["decision"], "border_applied")
        self.assertIn("border:kernel-north:0,3,0", north["preservedResults"])
        self.assertIn("border:kernel-south:0,4,0", south["preservedResults"])
        self.assertNotIn(north["decision"], {"qualified", "allowed"})

    def test_tile_seam_keeps_the_cross_seam_average(self):
        result = evaluate(payload(site="tile-seam", impulse=12))
        self.assertContract(result)
        self.assertEqual(result["decision"], "border_applied")
        self.assertIn("border:tile-seam:6,0,0", result["preservedResults"])

    def test_outside_read_and_stale_slot_and_ignored_halo_fail(self):
        outside = evaluate(payload(readOutside=True))
        self.assertEqual(outside["decision"], "rejected")
        self.assertIn("outside-retained-row", outside["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, outside["reasons"])
        self.assertIn("border:corner-nw:0,6,0", outside["preservedResults"])
        self.assertNotIn(outside["decision"], {"qualified", "allowed", "border_applied"})
        stale = evaluate(payload(site="corner-se", staleSlot=True))
        self.assertEqual(stale["decision"], "rejected")
        self.assertIn("stale-buffer-slot", stale["rejectedClaims"])
        self.assertIn("border:corner-se:0,4,0", stale["preservedResults"])
        halo = evaluate(payload(site="tile-seam", ignoreHalo=True))
        self.assertEqual(halo["decision"], "rejected")
        self.assertEqual(halo["rejectedClaims"], ["ignored-halo"])
        self.assertIn("border:tile-seam:6,0,0", halo["preservedResults"])
        self.assertIn("impulse:12", halo["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "site": "center"},
            {**valid, "impulse": 0},
            {**valid, "readOutside": "yes"},
            {k: v for k, v in valid.items() if k != "staleSlot"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
