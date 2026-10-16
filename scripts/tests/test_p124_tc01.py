"""Tests for TC-P124-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "filename": "clip.mov",
        "extension": "mov",
        "containerColorTag": None,
        "metadataColorTag": None,
        "rotationDegrees": None,
        "timingFrameRate": None,
        "timingTimebase": None,
        "detectedFacts": ["color-tag-absent", "rotation-absent", "timing-absent"],
        "userInterpretation": None,
        "assumedTransfer": None,
        "assumedDynamicRange": None,
    }
    base.update(overrides)
    return base


class TCP12401(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_untagged_media_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("color-tag-absent", result["preservedResults"])

    def test_extension_does_not_determine_transfer_or_range(self):
        result = evaluate(payload(
            assumedTransfer="rec709",
            assumedDynamicRange="sdr",
            detectedFacts=["transfer=rec709"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.EXTENSION_TRANSFER, result["rejectedClaims"])
        self.assertIn(_MODULE.EXTENSION_RANGE, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_contradictory_tags_stay_detected_when_interpretation_is_separate(self):
        result = evaluate(payload(
            containerColorTag="hlg",
            metadataColorTag="logc3",
            userInterpretation="operator-chose-logc3",
            detectedFacts=["container=hlg", "metadata=logc3", "color-tag-contradictory"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("userInterpretation=operator-chose-logc3", result["preservedResults"])
        self.assertNotIn("operator-chose-logc3", result["preservedResults"][3:])

    def test_silent_normalization_and_interpretation_as_fact_are_rejected(self):
        result = evaluate(payload(
            containerColorTag="hlg",
            metadataColorTag="logc3",
            assumedTransfer="hlg",
            detectedFacts=["container=hlg", "metadata=logc3", "operator-chose-logc3"],
            userInterpretation="operator-chose-logc3",
            rotationDegrees=None,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SILENT_NORMALIZATION, result["rejectedClaims"])
        self.assertIn(_MODULE.INTERPRETATION_AS_FACT, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait", rotationDegrees=90,
                                  detectedFacts=["color-tag-absent", "rotation=90"]))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
