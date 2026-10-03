"""TC-P045-01 neutral target invalidity."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p045_tc01", Path(__file__).resolve().parents[1] / "gates" / "p045_tc01.py"
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
        "patchId": "N18",
        "patchClass": "approved",
        "illumination": "neutral",
        "wholeImageAverage": False,
        "signalLevel": "0.18",
    }
    base.update(overrides)
    return base


class TcP04501(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P045-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("N18", result["preservedResults"])

    def test_approved_neutral_stays_provisional(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("signal:0.18", result["preservedResults"])
        self.assertIn("class:approved", result["preservedResults"])
        self.assertTrue(any("provisional" in item for item in result["reasons"]))
        self.assertIn(_MODULE.INTERVENTION, result["reasons"])

    def test_negative_whole_image_average_cannot_replace_the_target(self):
        result = evaluate(payload(wholeImageAverage=True, signalLevel="0.5"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["whole-image-average", "not-a-neutral-target"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("signal:0.5", result["preservedResults"])
        self.assertIn("N18", result["preservedResults"])

    def test_dark_patch_is_rejected_and_keeps_its_signal(self):
        result = evaluate(payload(patchClass="dark", signalLevel="0.02"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-neutral:dark", result["rejectedClaims"])
        self.assertIn("signal:0.02", result["preservedResults"])

    def test_colored_illumination_is_rejected(self):
        result = evaluate(payload(illumination="colored", patchId="N18-color"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("colored-illumination", result["rejectedClaims"])
        self.assertIn("N18-color", result["preservedResults"])
        self.assertIn("light:colored", result["preservedResults"])

    def test_mixed_pixels_are_rejected(self):
        result = evaluate(payload(patchClass="mixed", patchId="mix-1"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-neutral:mixed", result["rejectedClaims"])
        self.assertIn("mix-1", result["preservedResults"])

    def test_partial_clipping_is_rejected(self):
        result = evaluate(payload(patchClass="partial_clip", signalLevel="0.98"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-neutral:partial_clip", result["rejectedClaims"])
        self.assertIn("signal:0.98", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})

    def test_clipped_textured_and_specular_regions_fail(self):
        for kind in ("clipped", "textured", "specular", "misidentified"):
            result = evaluate(payload(patchClass=kind))
            self.assertEqual(result["decision"], "rejected")
            self.assertIn(f"invalid-neutral:{kind}", result["rejectedClaims"])
            self.assertIn("N18", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            [],
            {},
            {k: v for k, v in valid.items() if k != "patchId"},
            {**valid, "extra": True},
            {**valid, "patchClass": "grey"},
            {**valid, "wholeImageAverage": "true"},
            {**valid, "signalLevel": "0.180"},
            {**valid, "illumination": "D65"},
            {**valid, "patchId": ""},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
