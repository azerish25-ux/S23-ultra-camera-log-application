"""Tests for TC-P122-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc01",
        "repeat": "Repeat HDR-looking untagged clips, variable rates, and portrait rotation.",
        "filename": "portrait.mov",
        "detectedColorTag": None,
        "detectedDynamicRange": None,
        "detectedRotation": "portrait",
        "detectedTiming": "variable",
        "userTransfer": "arri-logc3",
        "userDynamicRange": "wide",
        "interpretationExplicit": True,
        "extensionTransfer": "rec709",
        "extensionDynamicRange": "sdr",
        "silentNormalization": False,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12201(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_explicit_interpretation_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("detectedColorTag=absent", result["preservedResults"])
        self.assertIn("detectedRotation=portrait", result["preservedResults"])
        self.assertIn("userTransfer=arri-logc3", result["preservedResults"])

    def test_extension_alone_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(
            userTransfer="rec709",
            userDynamicRange="sdr",
            interpretationExplicit=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_contradictory_tag_copied_from_extension_is_rejected(self):
        result = evaluate(payload(
            detectedColorTag="hlg",
            detectedDynamicRange="hdr",
            userTransfer="rec709",
            userDynamicRange="sdr",
            interpretationExplicit=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_explicit_user_choice_can_disagree_with_the_tag(self):
        result = evaluate(payload(
            detectedColorTag="hlg",
            detectedDynamicRange="hdr",
            userTransfer="rec709",
            userDynamicRange="sdr",
            interpretationExplicit=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_silent_normalization_is_rejected(self):
        result = evaluate(payload(silentNormalization=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SILENT_TOKEN, result["rejectedClaims"])

    def test_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[1]["version_sha256"] = "ab" * 32
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc01-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait rotation"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
