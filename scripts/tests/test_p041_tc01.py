"""TC-P041-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p041_tc01", Path(__file__).resolve().parents[1] / "gates" / "p041_tc01.py"
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
        "target": "approved",
        "illuminant": "D65",
        "provisional": False,
        "wholeImageAverage": False,
        "patchId": "neutral-18",
    }
    base.update(overrides)
    return base


class TcP04101(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P041-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertTrue(all(isinstance(item, str) and item for item in result["reasons"]))

    def test_whole_image_average_cannot_replace_a_neutral_target(self):
        result = evaluate(payload(wholeImageAverage=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["whole-image-average"])
        self.assertEqual(
            result["preservedResults"],
            ["patch:neutral-18", "target:approved", "illuminant:D65"],
        )
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertNotIn("measured-profile", result["preservedResults"])

    def test_clipped_patch_rejects_scale_calibration(self):
        result = evaluate(payload(target="clipped", patchId="clip-1"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:clipped"])
        self.assertIn("patch:clip-1", result["preservedResults"])
        self.assertIn("target:clipped", result["preservedResults"])

    def test_dark_patch_repeat_is_provisional_not_measured(self):
        result = evaluate(payload(target="dark", illuminant="tungsten", provisional=True, patchId="dark-1"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:dark"])
        self.assertEqual(
            result["preservedResults"],
            ["patch:dark-1", "target:dark", "illuminant:tungsten"],
        )
        self.assertIn("explicitly provisional; not a measured profile", result["openQuestions"])

    def test_colored_illumination_repeat_rejects_without_provisional_flag(self):
        result = evaluate(payload(target="colored", illuminant="colored", patchId="color-cast"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:colored"])
        self.assertIn("illuminant:colored", result["preservedResults"])
        self.assertIn("patch:color-cast", result["preservedResults"])

    def test_mixed_pixels_repeat_stays_provisional(self):
        result = evaluate(payload(target="mixed", provisional=True, patchId="mixed-edge"))
        self.assertEqual(result["decision"], "provisional")
        self.assertIn("target:mixed", result["preservedResults"])
        self.assertIn("patch:mixed-edge", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_partial_clip_repeat_rejects_scale(self):
        result = evaluate(payload(target="partial-clip", patchId="partial-1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:partial-clip"])
        self.assertIn("target:partial-clip", result["preservedResults"])

    def test_approved_patch_is_checked_and_not_a_measured_profile(self):
        result = evaluate(payload())
        self.assertEqual(result["decision"], "neutral_checked")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["openQuestions"], ["not a measured profile"])
        self.assertIn("patch:neutral-18", result["preservedResults"])
        self.assertEqual(_MODULE.INTERVENTION[:8], "Replace ")

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "target"},
            {**valid, "extra": True},
            {**valid, "target": "average"},
            {**valid, "illuminant": "D50"},
            {**valid, "provisional": "true"},
            {**valid, "wholeImageAverage": 1},
            {**valid, "patchId": ""},
            {**valid, "patchId": " pad"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
