"""Tests for TC-P123-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p123-import",
        "filename": "clip.mov",
        "extension": "mov",
        "colorTag": None,
        "rotationDegrees": 0,
        "timingMetadata": "absent",
        "detectedTransfer": None,
        "detectedDynamicRange": None,
        "extensionImpliedTransfer": "rec709",
        "extensionImpliedDynamicRange": "sdr",
        "userInterpretation": "possible-hlg",
        "assumedSourceType": None,
        "repeat": "hdr-untagged",
    }
    base.update(overrides)
    return base


class TCP12301(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Ambiguous imported signal")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Import media with absent or contradictory color tags, rotation, or timing metadata.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Separate detected facts from user interpretation and avoid silent normalization to an assumed source type.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Filename extension alone must not determine transfer or dynamic range.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.",
        )

    def test_untagged_facts_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertIsNone(kept["detectedFacts"]["transfer"])
        self.assertIsNone(kept["detectedFacts"]["dynamicRange"])
        self.assertEqual(kept["userInterpretation"], "possible-hlg")
        self.assertIsNone(result["preservedResults"][2])

    def test_extension_and_silent_normalization_are_rejected(self):
        result = evaluate(
            payload(detectedTransfer="rec709", detectedDynamicRange="sdr", assumedSourceType="video-sdr")
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-extension-determines-transfer-or-dynamic-range", result["rejectedClaims"])
        self.assertIn("silent-normalization-to-assumed-source-type", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["detectedFacts"]["transfer"], "rec709")
        self.assertEqual(result["preservedResults"][1]["userInterpretation"], "possible-hlg")

    def test_variable_rate_and_portrait_rotation_can_be_recorded(self):
        variable = evaluate(
            payload(
                evidenceId="p123-variable",
                colorTag="untagged",
                timingMetadata="variable",
                repeat="variable-rate",
            )
        )
        self.assert_contract(variable, "p123-variable")
        self.assertEqual(variable["decision"], "recorded")
        self.assertEqual(variable["preservedResults"][1]["detectedFacts"]["timingMetadata"], "variable")
        portrait = evaluate(
            payload(
                evidenceId="p123-portrait",
                colorTag="rec709",
                rotationDegrees=90,
                timingMetadata="constant",
                repeat="portrait-rotation",
            )
        )
        self.assert_contract(portrait, "p123-portrait")
        self.assertEqual(portrait["decision"], "recorded")
        self.assertEqual(portrait["preservedResults"][1]["detectedFacts"]["rotationDegrees"], 90)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(filename="clip.mp4"))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="variable-rate"))
        with self.assertRaises(ValueError):
            evaluate(payload(rotationDegrees=45, repeat="portrait-rotation"))
