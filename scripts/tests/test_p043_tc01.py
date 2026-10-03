"""TC-P043-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p043_tc01", Path(__file__).resolve().parents[1] / "gates" / "p043_tc01.py"
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
        "patchId": "neutral-18",
        "defect": "none",
        "approvedNeutral": True,
        "wholeImageAverage": "0.42",
        "useAverageAsNeutral": False,
        "claimMeasuredProfile": False,
    }
    base.update(overrides)
    return base


class TcP04301(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P043-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("patch:neutral-18", result["preservedResults"])
        self.assertIn("average:0.42", result["preservedResults"])

    def test_constants_match_the_case(self):
        self.assertIn("clipped, textured, specular", _MODULE.INTERVENTION)
        self.assertIn("provisional", _MODULE.EXPECTED)
        self.assertIn("Whole-image average brightness", _MODULE.NEGATIVE)

    def test_whole_image_average_cannot_replace_the_neutral(self):
        result = evaluate(payload(useAverageAsNeutral=True, approvedNeutral=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "neutral_recorded", "provisional"})
        self.assertIn("whole-image-average", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("average:0.42", result["preservedResults"])

    def test_dark_patch_stays_provisional(self):
        result = evaluate(payload(defect="dark", approvedNeutral=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("defect:dark", result["rejectedClaims"])
        self.assertIn("defect:dark", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertIn("provisional:dark", result["openQuestions"])

    def test_colored_illumination_stays_provisional(self):
        result = evaluate(payload(defect="colored", approvedNeutral=False))
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("defect:colored", result["preservedResults"])
        self.assertIn("average:0.42", result["preservedResults"])

    def test_mixed_pixels_stay_provisional(self):
        result = evaluate(payload(defect="mixed", approvedNeutral=False))
        self.assertEqual(result["decision"], "provisional")
        self.assertIn("defect:mixed", result["rejectedClaims"])
        self.assertIn("patch:neutral-18", result["preservedResults"])

    def test_partial_clip_rejects_scale_calibration(self):
        result = evaluate(payload(defect="partial-clip", approvedNeutral=False))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertEqual(result["rejectedClaims"], ["defect:partial-clip"])
        self.assertIn("scale calibration rejected", result["reasons"])
        self.assertIn("average:0.42", result["preservedResults"])

    def test_measured_claim_on_a_clipped_patch_is_fabricated(self):
        result = evaluate(payload(defect="clipped", approvedNeutral=False, claimMeasuredProfile=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("fabricated-measured-profile", result["rejectedClaims"])
        self.assertIn("patch:neutral-18", result["preservedResults"])

    def test_approved_patch_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "neutral_recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("average:0.42", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "defect": "hot"},
            {**valid, "patchId": ""},
            {**valid, "wholeImageAverage": "0.420"},
            {**valid, "useAverageAsNeutral": "false"},
            {**valid, "extra": True},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
