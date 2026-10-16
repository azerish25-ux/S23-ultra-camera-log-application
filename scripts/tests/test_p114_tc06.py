"""Tests for TC-P114-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p114_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p114_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p114-evidence",
        "repeat": "moving subjects",
        "shutter_angle_degrees": 180.0,
        "fps": 24.0,
        "contains_estimated": False,
        "disclosed": True,
        "labelled_as_longer_sensor_exposure": False,
        "frames": [{"origin": "captured", "weight": 1.0}],
        "independent_foreground_motion": True,
        "applied_global_shear": False,
        "advertised_as_universal_removal": False,
        "correction_restricted": True,
        "readout_known": True,
    }
    base.update(overrides)
    return base


class TCP11406(unittest.TestCase):
    def assert_contract(self, result, evidence="p114-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P114-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_restricted_correction_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertNotIn("qualified", result["reasons"])

    def test_universal_shear_claim_is_rejected(self):
        result = evaluate(payload(
            applied_global_shear=True,
            advertised_as_universal_removal=True,
            correction_restricted=False,
            repeat="pans",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("global-shear-advertised-as-universal-rolling-shutter-removal", result["rejectedClaims"])
        self.assertIn("unjustified-global-warp", result["rejectedClaims"])

    def test_unknown_readout_and_unrestricted_warp_are_rejected(self):
        readout = evaluate(payload(
            independent_foreground_motion=False,
            applied_global_shear=True,
            correction_restricted=True,
            readout_known=False,
            repeat="unknown readout timing",
        ))
        self.assertIn("unknown-readout-timing", readout["rejectedClaims"])
        warp = evaluate(payload(applied_global_shear=True, correction_restricted=False, repeat="vibrations"))
        self.assertIn("unjustified-global-warp", warp["rejectedClaims"])
        self.assertNotIn("global-shear-advertised-as-universal-rolling-shutter-removal", warp["rejectedClaims"])
        self.assertIn("p114-evidence", warp["preservedResults"])

    def test_scope_rules_still_apply(self):
        hidden = evaluate(payload(
            frames=[{"origin": "estimated", "weight": 1.0}],
            contains_estimated=True,
            disclosed=False,
        ))
        self.assertIn("hidden-hallucination", hidden["rejectedClaims"])
        weights = evaluate(payload(frames=[{"origin": "captured", "weight": 0.5}, {"origin": "captured", "weight": 0.2}]))
        self.assertIn("unnormalized-temporal-weights", weights["rejectedClaims"])
        labelled = evaluate(payload(labelled_as_longer_sensor_exposure=True))
        self.assertIn("labelled-as-longer-sensor-exposure", labelled["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p114-pans"
        result = evaluate(payload(evidenceId=evidence, repeat="pans"))
        self.assert_contract(result, evidence)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(readout_known="yes"))
