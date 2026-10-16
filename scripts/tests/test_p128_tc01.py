"""Tests for TC-P128-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "filename": "portrait-untagged.mov",
        "colorTag": "absent",
        "rotationDegrees": 90,
        "reportedRotation": 90,
        "timingMetadata": "variable",
        "reportedTiming": "variable",
        "detectedTransfer": "unspecified",
        "detectedDynamicRange": "unspecified",
        "userTransfer": "rec709",
        "userDynamicRange": "sdr",
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12801(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_untagged_import_keeps_facts_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("detectedTransfer=unspecified", result["preservedResults"])
        self.assertIn("userTransfer=rec709", result["preservedResults"])
        self.assertIn("extension=mov extension-not-used-as-detected-fact", result["reasons"])
        self.assertIn("rotation=90", result["reasons"])
        self.assertIn("timing=variable", result["reasons"])
        self.assertIn("frameAccount=6/6", blob(result))

    def test_filename_extension_does_not_assign_transfer(self):
        result = evaluate(payload(detectedTransfer="rec709", detectedDynamicRange="sdr"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p128-evidence", result["preservedResults"])

    def test_contradictory_tags_stay_contradictory(self):
        result = evaluate(payload(
            colorTag="contradictory",
            detectedTransfer="contradictory",
            detectedDynamicRange="contradictory",
            userTransfer="hlg",
            userDynamicRange="hdr",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("detectedTransfer=contradictory", result["preservedResults"])
        self.assertIn("userTransfer=hlg", result["preservedResults"])

    def test_portrait_rotation_is_not_rewritten_to_landscape(self):
        result = evaluate(payload(reportedRotation=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ROTATION_TOKEN, result["rejectedClaims"])

    def test_variable_timing_is_not_rewritten_to_constant(self):
        result = evaluate(payload(reportedTiming="constant"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.TIMING_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 3, 4, 5, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])
        self.assertIn("p128-evidence", result["preservedResults"])

    def test_spot_check_only_is_rejected_inside_the_case(self):
        result = evaluate(payload(spot_check_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("spot-check-only", result["rejectedClaims"])
        self.assertIn("frameAccount=6/6", blob(result))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
