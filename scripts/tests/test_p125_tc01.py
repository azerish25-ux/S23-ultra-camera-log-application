"""Tests for TC-P125-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p125-import",
        "repeat": "hdr-looking-untagged",
        "filenameExtension": "mov",
        "colorTag": None,
        "detectedTransfer": None,
        "interpretedTransfer": None,
        "detectedDynamicRange": None,
        "interpretedDynamicRange": None,
        "rotationDegrees": None,
        "interpretedRotation": None,
        "timingRate": None,
        "interpretedTimingRate": None,
    }
    base.update(overrides)
    return base


class TCP12501(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-import"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-01")
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
        self.assertEqual(_MODULE.REPEAT, "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.")

    def test_absent_tags_stay_unassumed(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        kept = result["preservedResults"][1]
        self.assertIsNone(kept["detectedTransfer"])
        self.assertIsNone(kept["interpretedTransfer"])
        self.assertEqual(kept["filenameExtension"], "mov")

    def test_filename_extension_does_not_set_transfer(self):
        result = evaluate(payload(interpretedTransfer="mov", interpretedDynamicRange="mov"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FILENAME_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.SILENT_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][1]["detectedTransfer"], None)

    def test_contradictory_tag_keeps_both_facts(self):
        result = evaluate(
            payload(
                repeat="portrait-rotation",
                colorTag="bt.709",
                detectedTransfer="hlg",
                interpretedTransfer="hlg",
                detectedDynamicRange="hdr",
                interpretedDynamicRange="hdr",
                rotationDegrees=90,
                interpretedRotation=90,
                timingRate="24",
                interpretedTimingRate="24",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][1]
        self.assertEqual(kept["colorTag"], "bt.709")
        self.assertEqual(kept["detectedTransfer"], "hlg")
        self.assertEqual(kept["rotationDegrees"], 90)

    def test_variable_rate_fact_is_not_rewritten(self):
        result = evaluate(
            payload(
                evidenceId="p125-variable",
                repeat="variable-rates",
                timingRate="variable",
                interpretedTimingRate="variable",
            )
        )
        self.assert_contract(result, "p125-variable")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["timingRate"], "variable")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(rotationDegrees=15))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="other"))
