"""TC-P042-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p042_tc01", Path(__file__).resolve().parents[1] / "gates" / "p042_tc01.py"
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
        "regionClass": "clipped",
        "repeat": "dark_patches",
        "meanBrightness": "18.5",
        "provisional": False,
    }
    base.update(overrides)
    return base


class TcP04201(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P042-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Replace the approved neutral patch with a clipped, textured, specular, "
            "or incorrectly identified region.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Reject scale calibration or retain an explicitly provisional result "
            "rather than fabricating a measured profile.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Whole-image average brightness cannot substitute for a known neutral target.",
        )

    def test_whole_image_average_is_rejected(self):
        result = evaluate(payload(regionClass="whole_image", provisional=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["whole-image-average"])
        self.assertIn("mean-brightness:18.5", result["preservedResults"])
        self.assertIn("patch:neutral-18", result["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertNotIn("measured-profile", result["preservedResults"])

    def test_repeat_dark_patches_rejects_scale(self):
        result = evaluate(payload(repeat="dark_patches", regionClass="approved_neutral"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("repeat:dark_patches", result["preservedResults"])
        self.assertIn("invalid-neutral:approved_neutral", result["rejectedClaims"])
        self.assertIn("mean-brightness:18.5", result["preservedResults"])

    def test_repeat_colored_illumination_rejects_scale(self):
        result = evaluate(
            payload(repeat="colored_illumination", regionClass="textured", meanBrightness="40")
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertIn("repeat:colored_illumination", result["preservedResults"])
        self.assertIn("mean-brightness:40", result["preservedResults"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])

    def test_provisional_clipped_patch_is_not_a_measured_profile(self):
        result = evaluate(payload(regionClass="clipped", provisional=True, repeat="partial_clipping"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("region:clipped", result["preservedResults"])
        self.assertIn("provisional is not a measured profile", result["openQuestions"])
        self.assertIn("mean-brightness:18.5", result["preservedResults"])

    def test_mixed_pixels_inventory_survives_rejection(self):
        result = evaluate(payload(regionClass="misidentified", repeat="mixed_pixels"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("repeat:mixed_pixels", result["rejectedClaims"])
        self.assertIn("patch:neutral-18", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "regionClass": "neutral"},
            {**valid, "provisional": "true"},
            {**valid, "meanBrightness": "18.50"},
            {**valid, "repeat": "daylight"},
            {k: v for k, v in valid.items() if k != "patchId"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
