"""Tests for TC-P154-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def setup(**overrides):
    value = {
        "model": "SM-S911B",
        "firmwareApplicability": "unverified-public-source",
        "method": "public-document-survey",
        "seeds": "none-deterministic-host",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture")
    base.update({
        "favorableOutputs": ["graded-still"],
        "failedExperiments": ["rejected-firmware-claim", "storage-bottleneck"],
        "setup": setup(),
        "promotionalReelOnly": False,
    })
    base.update(overrides)
    return base


class TCP15408(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_experiments_and_setup_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["reconstructable"])
        self.assertIn("storage-bottleneck", result["preservedResults"][3]["failedExperiments"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "promotional-reel-substitutes-for-engineering-archive")

    def test_promotional_reel_cannot_replace_the_archive(self):
        result = evaluate(payload(promotionalReelOnly=True, favorableOutputs=["reel"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertFalse(result["preservedResults"][3]["reconstructable"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_omitted_failed_experiments_are_rejected(self):
        result = evaluate(payload(failedExperiments=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FAILED_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_omitted_setup_is_rejected(self):
        result = evaluate(payload(setup=setup(method="omitted")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SETUP_OMITTED, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][3]["reconstructable"])

    def test_unrecorded_missing_component_is_still_rejected(self):
        result = evaluate(payload(missingComponents=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MISSING_COMPONENT_UNRECORDED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(setup={"model": "SM-S911B"}))
        with self.assertRaises(ValueError):
            evaluate(payload(promotionalReelOnly="yes"))
