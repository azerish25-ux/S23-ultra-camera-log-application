"""Tests for TC-P156-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def archive(**overrides):
    value = {
        "favorableOutputs": ["clip-a"],
        "failedExperiments": ["unverified-image-hypothesis"],
        "setupDetails": ["serial-R5CW10S23A", "image-digest"],
        "promotionalReelOnly": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture")
    base.update({"archive": archive()})
    base.update(overrides)
    return base


class TCP15608(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_experiments_and_setup_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["promotionalReelOnly"])
        self.assertIn("unverified-image-hypothesis", result["preservedResults"][3]["failedExperiments"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")

    def test_promotional_reel_cannot_substitute_for_the_archive(self):
        result = evaluate(payload(archive=archive(promotionalReelOnly=True, failedExperiments=[])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.INCOMPLETE_ARCHIVE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_omitting_setup_details_is_rejected(self):
        result = evaluate(payload(archive=archive(setupDetails=[])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INCOMPLETE_ARCHIVE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_similar_name_only_is_still_rejected(self):
        result = evaluate(payload(similar_name_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SIMILAR_NAME_ONLY, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(archive=archive(promotionalReelOnly="reel")))
