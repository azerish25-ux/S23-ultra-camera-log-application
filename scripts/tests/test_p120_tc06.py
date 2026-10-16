"""Tests for TC-P120-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p120_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p120_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def honest_report(**overrides):
    value = {
        "shutter_angle": 180.0,
        "fps": 24.0,
        "exposure_seconds": (180.0 / 360.0) / 24.0,
        "interpolation_fraction": 0.0,
        "estimated_disclosed": False,
        "stabilization_crop_fraction": 0.0,
        "rolling_shutter_readout": "measured",
        "correction_applied": True,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p120-evidence",
        "repeat": "Repeat",
        "combinationPassed": True,
        "report": honest_report(),
        "foregroundVelocity": 3.0,
        "backgroundVelocity": 1.0,
        "globalShear": 0.01,
        "readoutSeconds": 0.01,
        "advertisedUniversal": False,
        "restrictedToBackground": True,
    }
    base.update(overrides)
    return base


class TCP12006(unittest.TestCase):
    def assert_contract(self, result, evidence="p120-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P120-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_restricted_measured_shear_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("shear matches background" in item for item in result["reasons"]))

    def test_universal_shear_claim_is_rejected(self):
        result = evaluate(payload(advertisedUniversal=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unrestricted_foreground_warp_is_rejected(self):
        result = evaluate(payload(restrictedToBackground=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WARP_TOKEN, result["rejectedClaims"])

    def test_unknown_readout_cannot_apply_correction(self):
        result = evaluate(payload(
            readoutSeconds=None,
            globalShear=0.0,
            report=honest_report(rolling_shutter_readout="unknown", correction_applied=True),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction-applied-with-unknown-readout", result["rejectedClaims"])

    def test_unknown_readout_with_a_shear_is_rejected(self):
        result = evaluate(payload(
            readoutSeconds=None,
            globalShear=0.01,
            report=honest_report(rolling_shutter_readout="unknown", correction_applied=False),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.READOUT_TOKEN, result["rejectedClaims"])

    def test_withheld_correction_on_unknown_readout_is_recorded(self):
        result = evaluate(payload(
            readoutSeconds=None,
            globalShear=0.0,
            restrictedToBackground=True,
            report=honest_report(rolling_shutter_readout="unknown", correction_applied=False),
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_shear_mismatch_is_rejected(self):
        result = evaluate(payload(globalShear=0.2))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SHEAR_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p120-pan"
        result = evaluate(payload(evidenceId=evidence, repeat="pans"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
