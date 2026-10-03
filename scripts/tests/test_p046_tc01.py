"""TC-P046-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p046_tc01", Path(__file__).resolve().parents[1] / "gates" / "p046_tc01.py"
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
        "patchId": "gray-18",
        "region": "approved",
        "wholeImageAverage": False,
        "provisional": False,
        "meanChannels": [1000, 1000, 1000],
    }
    base.update(overrides)
    return base


class TcP04601(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P046-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_approved_patch_does_not_fabricate_a_profile(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "withheld")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("patch:gray-18", result["preservedResults"])
        self.assertIn("mean:1000,1000,1000", result["preservedResults"])
        self.assertEqual(_MODULE.INTERVENTION[:8], "Replace ")
        self.assertIn("provisional", _MODULE.EXPECTED)

    def test_explicit_provisional_is_not_a_measured_profile(self):
        result = evaluate(payload(provisional=True, region="clipped", meanChannels=[4000, 20, 20]))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("region:clipped", result["preservedResults"])
        self.assertIn("mean:4000,20,20", result["preservedResults"])
        self.assertIn("provisional:true", result["preservedResults"])

    def test_dark_patch_is_rejected(self):
        result = evaluate(payload(region="dark", meanChannels=[2, 1, 0]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["region:dark"])
        self.assertIn("mean:2,1,0", result["preservedResults"])
        self.assertIn("neutral target invalid", result["openQuestions"])

    def test_colored_illumination_is_rejected(self):
        result = evaluate(payload(region="colored", meanChannels=[80, 400, 900]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["region:colored"])
        self.assertIn("patch:gray-18", result["preservedResults"])
        self.assertIn("mean:80,400,900", result["preservedResults"])

    def test_mixed_pixels_stay_provisional(self):
        result = evaluate(payload(region="mixed-pixels", provisional=True, meanChannels=[10, 20, 30]))
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("region:mixed-pixels", result["preservedResults"])
        self.assertIn("mean:10,20,30", result["preservedResults"])

    def test_partial_clip_is_rejected(self):
        result = evaluate(payload(region="partial-clip", meanChannels=[4095, 1000, 1000]))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["region:partial-clip"])
        self.assertIn("mean:4095,1000,1000", result["preservedResults"])

    def test_whole_image_average_cannot_replace_a_neutral(self):
        result = evaluate(payload(wholeImageAverage=True, provisional=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertEqual(result["rejectedClaims"], ["whole-image-average"])
        self.assertIn("mean:1000,1000,1000", result["preservedResults"])
        self.assertIn("whole-image-average:true", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "region"},
            {**valid, "extra": True},
            {**valid, "region": "sky"},
            {**valid, "wholeImageAverage": "true"},
            {**valid, "meanChannels": [1, 2]},
            {**valid, "meanChannels": [True, 1, 1]},
            {**valid, "patchId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
