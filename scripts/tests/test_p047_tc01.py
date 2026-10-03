"""TC-P047-01 invalid neutral targets are not a measured profile."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p047_tc01", Path(__file__).resolve().parents[1] / "gates" / "p047_tc01.py"
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
        "patchKind": "approved-neutral",
        "wholeImageAverage": False,
        "sourceFrameId": "frame-1",
        "roi": "32x32+8+8",
        "reportedBrightness": "0.18",
    }
    base.update(overrides)
    return base


class TcP04701(unittest.TestCase):
    def assertContract(self, result):
        self.assertEqual(tuple(result), _KEYS)
        self.assertEqual(result["caseId"], "TC-P047-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertTrue(result["reasons"])
        self.assertIn("frame:frame-1", result["preservedResults"])
        self.assertIn("roi:32x32+8+8", result["preservedResults"])

    def test_constants(self):
        self.assertIn("incorrectly identified", _MODULE.INTERVENTION)
        self.assertIn("provisional", _MODULE.EXPECTED)
        self.assertIn("Whole-image average brightness", _MODULE.NEGATIVE)

    def test_approved_neutral_stays_provisional(self):
        result = evaluate(payload())
        self.assertContract(result)
        self.assertEqual(result["decision"], "provisional")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("patch:approved-neutral", result["preservedResults"])
        self.assertIn("brightness:0.18", result["preservedResults"])
        self.assertIn("scale remains provisional on the host fixture", result["openQuestions"])

    def test_dark_patch_is_rejected(self):
        result = evaluate(payload(patchKind="dark", reportedBrightness="0.02"))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["invalid-neutral:dark"])
        self.assertIn("brightness:0.02", result["preservedResults"])
        self.assertIn("measured profile not fabricated", result["openQuestions"])

    def test_colored_illumination_is_rejected(self):
        result = evaluate(payload(patchKind="colored-illumination", reportedBrightness="0.4"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("invalid-neutral:colored-illumination", result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})
        self.assertIn("frame:frame-1", result["preservedResults"])

    def test_mixed_pixels_and_partial_clip_repeat(self):
        for kind in ("mixed-pixels", "partial-clip", "clipped", "textured", "specular", "misidentified"):
            result = evaluate(payload(patchKind=kind))
            self.assertEqual(result["decision"], "rejected")
            self.assertEqual(result["rejectedClaims"], ["invalid-neutral:" + kind])
            self.assertIn("patch:" + kind, result["preservedResults"])
            self.assertIn("roi:32x32+8+8", result["preservedResults"])

    def test_whole_image_average_cannot_substitute(self):
        result = evaluate(payload(wholeImageAverage=True))
        self.assertContract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], ["whole-image-average"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("brightness:0.18", result["preservedResults"])
        self.assertNotIn(result["decision"], {"qualified", "allowed", "provisional"})

    def test_average_does_not_repair_a_dark_patch(self):
        result = evaluate(payload(patchKind="dark", wholeImageAverage=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(
            result["rejectedClaims"],
            ["invalid-neutral:dark", "whole-image-average"],
        )
        self.assertIn("patch:dark", result["preservedResults"])

    def test_invalid_payload_raises(self):
        valid = payload()
        cases = [
            None,
            {},
            {**valid, "patchKind": "grey"},
            {**valid, "wholeImageAverage": 1},
            {**valid, "reportedBrightness": "0.180"},
            {**valid, "reportedBrightness": "-0.1"},
            {k: v for k, v in valid.items() if k != "roi"},
        ]
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
