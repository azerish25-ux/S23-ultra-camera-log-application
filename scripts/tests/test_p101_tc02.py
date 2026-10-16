"""Tests for TC-P101-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc02",
        "repeat": "landscape",
        "sourceWidth": 4,
        "sourceHeight": 2,
        "tensorSize": 4,
        "channelOrder": "rgb",
        "recordedChannelOrder": "rgb",
        "preparation": "letterbox",
        "stretchRecorded": False,
    }
    base.update(overrides)
    return base


class TCP10102(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_letterbox_restores_landscape_corners(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = " ".join(result["reasons"])
        self.assertIn("scale=1.000000 padX=0.000000 padY=1.000000 channelOrder=rgb", text)
        self.assertIn(
            "restoredCorners=(0.000000,0.000000);(3.000000,0.000000);(0.000000,1.000000);(3.000000,1.000000)",
            text,
        )

    def test_letterbox_restores_portrait_corners(self):
        result = evaluate(payload(sourceWidth=2, sourceHeight=4, repeat="portrait"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        text = " ".join(result["reasons"])
        self.assertIn("scale=1.000000 padX=1.000000 padY=0.000000 channelOrder=rgb", text)
        self.assertIn(
            "restoredCorners=(0.000000,0.000000);(1.000000,0.000000);(0.000000,3.000000);(1.000000,3.000000)",
            text,
        )

    def test_unrecorded_stretch_is_rejected(self):
        result = evaluate(payload(preparation="stretch", stretchRecorded=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])

    def test_swapped_channels_are_rejected(self):
        result = evaluate(payload(channelOrder="bgr", recordedChannelOrder="rgb"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unrecorded-stretching-swapped-color-channels-fail", result["rejectedClaims"])
        self.assertIn("channelOrder=bgr", " ".join(result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc02-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait", sourceWidth=2, sourceHeight=4))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceWidth=8, sourceHeight=8))
