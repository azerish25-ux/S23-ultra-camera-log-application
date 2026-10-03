"""TC-P050-03 border policy keeps halos inside retained rows."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p050_tc03", Path(__file__).resolve().parents[1] / "gates" / "p050_tc03.py"
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
        "place": "tl",
        "feature": "impulse",
        "halo": 2,
        "retainedRows": 4,
        "rowLimit": 8,
        "readOutside": False,
        "ignoreHalo": False,
        "staleRead": False,
    }
    base.update(overrides)
    return base


class TcP05003(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P050-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("policy:replicate-nearest-retained-sample", result["preservedResults"])

    def test_constants(self):
        self.assertIn("image boundary", _MODULE.INTERVENTION)
        self.assertIn("border policy", _MODULE.EXPECTED)
        self.assertIn("required halos", _MODULE.NEGATIVE)

    def test_repeat_all_four_corners(self):
        for place in ("tl", "tr", "bl", "br"):
            result = evaluate(payload(place=place, feature="edge"))
            self.assertContract(result)
            self.assertEqual(result["decision"], "border_applied")
            self.assertEqual(result["rejectedClaims"], [])
            self.assertIn(f"place:{place}", result["preservedResults"])
            self.assertIn("feature:edge", result["preservedResults"])
            self.assertTrue(any("no stale read" in item for item in result["reasons"]))

    def test_repeat_kernel_support_boundaries(self):
        for place in ("north", "east", "south", "west", "seam"):
            result = evaluate(payload(place=place, feature="impulse", halo=1, retainedRows=2))
            self.assertEqual(result["decision"], "border_applied")
            self.assertIn(f"place:{place}", result["preservedResults"])
            self.assertIn("halo:1", result["preservedResults"])
            self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_outside_read_and_ignored_halo_fail(self):
        outside = evaluate(payload(readOutside=True))
        self.assertEqual(outside["decision"], "rejected")
        self.assertIn("outside-retained-rows", outside["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, outside["reasons"])
        self.assertIn("place:tl", outside["preservedResults"])
        self.assertNotIn(outside["decision"], {"qualified", "allowed", "border_applied"})
        ignored = evaluate(payload(ignoreHalo=True, staleRead=True, place="seam"))
        self.assertEqual(ignored["decision"], "rejected")
        self.assertIn("ignored-halo", ignored["rejectedClaims"])
        self.assertIn("stale-read", ignored["rejectedClaims"])
        self.assertIn("place:seam", ignored["preservedResults"])
        self.assertIn("feature:impulse", ignored["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "place": "center"},
            {**valid, "halo": 0},
            {**valid, "retainedRows": 1},
            {**valid, "readOutside": 1},
            {k: v for k, v in valid.items() if k != "feature"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
