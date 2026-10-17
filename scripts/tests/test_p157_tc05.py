"""Tests for TC-P157-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "sample receipt",
        "menuExpanded": True,
        "newlyVisibleSetting": "raw-stream-mode",
        "settingUsedAsCaptureProof": False,
        "acquisitionHypothesis": "fail",
        "checks": {
            "sampleReceipt": False,
            "decodedFidelity": False,
            "sustainedCadence": False,
            "thermal": False,
        },
        "validSensorFrames": 0,
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15705(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_hypothesis_on_an_expanded_menu_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["acquisitionHypothesis"], "fail")
        self.assertEqual(result["preservedResults"][3]["validSensorFrames"], 0)
        self.assertEqual(_MODULE.CASE["name"], "Advertised unlock without delivery")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "visible-setting-is-not-useful-capture")

    def test_passing_the_hypothesis_without_frames_is_rejected(self):
        result = evaluate(payload(acquisitionHypothesis="pass"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HYPOTHESIS_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_a_newly_visible_setting_is_not_useful_capture(self):
        result = evaluate(payload(settingUsedAsCaptureProof=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_unlocked_claim_without_captured_output_is_rejected(self):
        result = evaluate(payload(experiments=[_GATE.unlocked_metadata_experiment()]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNLOCKED_WITHOUT_OUTPUT, result["rejectedClaims"])
        self.assertIn(_GATE.ORACLE, result["reasons"])
        self.assertIn("mutant rejected: " + _GATE.MUTANT, result["reasons"])
        self.assertEqual(
            result["preservedResults"][1]["unlockedWithoutOutput"],
            ["advertised-stream-metadata"],
        )

    def test_delivered_frames_and_checks_can_be_recorded(self):
        result = evaluate(payload(
            acquisitionHypothesis="pass",
            settingUsedAsCaptureProof=True,
            validSensorFrames=3,
            checks={
                "sampleReceipt": True,
                "decodedFidelity": True,
                "sustainedCadence": True,
                "thermal": True,
            },
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc05-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="thermal checks"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(validSensorFrames=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(acquisitionHypothesis="maybe"))
