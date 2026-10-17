"""Tests for TC-P149-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p149_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p149_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="warm starts")
    base.update(overrides)
    return base


class TCP14905(unittest.TestCase):
    def assert_contract(self, result, evidence="p149-thermal-endurance"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P149-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reduced_preview_under_warmth_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][3]["optionalPreviewReduced"])
        self.assertEqual(result["preservedResults"][3]["thermalStatus"], "moderate")
        self.assertFalse(result["preservedResults"][3]["physicalPass"])
        self.assertEqual(_MODULE.CASE["name"], "Thermal safety pressure")

    def test_bypassing_protection_to_hold_the_rate_is_rejected(self):
        result = evaluate(payload(
            thermalStatus="severe",
            continueCapture=True,
            controlledStop=False,
            advertisedFpsClaimed=True,
            optionalPreviewReduced=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.THERMAL_IGNORED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn(_GATE.THERMAL_RULE, " ".join(result["reasons"]))

    def test_ignoring_severe_pressure_without_an_advertised_fps_is_rejected(self):
        result = evaluate(payload(
            thermalStatus="severe",
            continueCapture=True,
            controlledStop=False,
            advertisedFpsClaimed=False,
            optionalPreviewReduced=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THERMAL_IGNORED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_stopping_capture_is_recorded(self):
        result = evaluate(payload(
            thermalStatus="critical",
            continueCapture=False,
            controlledStop=True,
            advertisedFpsClaimed=False,
            optionalPreviewReduced=False,
            footagePreserved=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][3]["pressureResolved"])
        self.assertFalse(result["preservedResults"][3]["continueCapture"])

    def test_unmeasured_envelope_stays_unavailable(self):
        result = evaluate(payload(envelopeStatus="recorded", measuredOnDevice=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.ENVELOPE_WITHOUT_MEASUREMENT, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["physicalPass"])

    def test_short_sample_frame_rate_guarantee_is_rejected(self):
        result = evaluate(payload(sampleDurationSeconds=4, frameRateGuaranteeClaimed=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.FRAME_RATE_FROM_SHORT_SAMPLE, result["rejectedClaims"])
        self.assertTrue(result["preservedResults"][3]["shortSample"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p149-tc05-charging"
        result = evaluate(payload(evidenceId=evidence, repeat="charging"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(thermalStatus="meltdown"))
        with self.assertRaises(ValueError):
            evaluate(payload(continueCapture="yes"))
