"""Tests for TC-P104-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc02",
        "orientation": "portrait",
        "sourceWidth": 1080,
        "sourceHeight": 1920,
        "resize": "letterbox",
        "geometryRecorded": True,
        "channelOrder": "rgb",
        "expectedChannelOrder": "rgb",
        "cornersRestored": True,
    }
    base.update(overrides)
    return base


class TCP10402(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_letterbox_restores_corners(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("source:1080x1920", result["preservedResults"])
        self.assertIn("corners-restored:true", result["preservedResults"])

    def test_negative_unrecorded_stretch_and_swapped_channels(self):
        stretch = evaluate(payload(resize="stretch", geometryRecorded=False))
        self.assertEqual(stretch["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, stretch["rejectedClaims"])
        self.assertIn("resize:stretch", stretch["preservedResults"])
        swapped = evaluate(payload(channelOrder="bgr"))
        self.assertEqual(swapped["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, swapped["rejectedClaims"])
        self.assertIn("channel-order:bgr", swapped["preservedResults"])
        self.assertIn(_MODULE.NEGATIVE, swapped["reasons"])

    def test_evidence_change_repeats_orientations(self):
        evidence = "p104-tc02-landscape"
        result = evaluate(payload(evidenceId=evidence, orientation="landscape", sourceWidth=1920, sourceHeight=1080))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        rotated = evaluate(payload(orientation="rotated", sourceWidth=720, sourceHeight=1280))
        self.assertEqual(rotated["decision"], "recorded")
        self.assertIn("orientation:rotated", rotated["preservedResults"])

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(sourceWidth=100, sourceHeight=100),
            payload(orientation="square"),
            payload(resize="squash"),
            payload(cornersRestored=1),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
