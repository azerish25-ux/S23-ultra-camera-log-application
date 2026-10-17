"""Tests for TC-P154-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="moving subjects")
    base.update({
        "exposureCount": 3,
        "presentedAs": "computational-acquisition",
        "labeledComputational": True,
        "motionArtifactsMeasured": True,
        "retainedInformationMeasured": True,
        "provenanceRetained": True,
    })
    base.update(overrides)
    return base


class TCP15406(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_labeled_merge_with_separate_measurements_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["exposureCount"], 3)
        self.assertTrue(result["preservedResults"][3]["provenanceRetained"])
        self.assertEqual(_MODULE.CASE["name"], "Computational capture overclaim")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "attractive-merge-erased-source-provenance")

    def test_erased_provenance_is_rejected(self):
        result = evaluate(payload(provenanceRetained=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_merge_presented_as_a_single_exposure_is_rejected(self):
        result = evaluate(payload(
            presentedAs="single-unchanged-sensor-exposure",
            labeledComputational=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PRESENTED_AS_SINGLE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unmeasured_motion_or_retained_information_is_rejected(self):
        result = evaluate(payload(motionArtifactsMeasured=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_SEPARATE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.PRESENTED_AS_SINGLE, result["rejectedClaims"])

    def test_complete_firmware_claim_is_still_rejected(self):
        result = evaluate(payload(claimsCompleteFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.COMPLETE_FIRMWARE_CLAIM, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc06-temporal-ghosts"
        result = evaluate(payload(evidenceId=evidence, repeat="temporal ghosts"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(exposureCount=0))
        with self.assertRaises(ValueError):
            evaluate(payload(presentedAs="pretty"))
