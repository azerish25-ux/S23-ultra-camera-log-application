"""Tests for TC-P116-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def timeline(**overrides):
    value = {
        "captured": [
            {"time": 0.0, "value": 0.0, "origin": "captured"},
            {"time": 1.0, "value": 2.0, "origin": "captured"},
        ],
        "estimated": [{"time": 0.5, "value": 1.0, "origin": "estimated"}],
        "withheldMidpoint": {"time": 0.5, "value": 1.0},
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p116-evidence",
        "repeat": "Repeat",
        "foregroundVelocity": 3.0,
        "backgroundVelocity": 1.0,
        "globalShear": 0.01,
        "readoutSeconds": 0.01,
        "advertisedUniversal": False,
        "restrictedToBackground": True,
    }
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11606(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))

    def test_restricted_background_shear_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_universal_shear_advertisement_is_rejected(self):
        result = evaluate(payload(advertisedUniversal=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unrestricted_foreground_warp_is_rejected(self):
        result = evaluate(payload(restrictedToBackground=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WARP_TOKEN, result["rejectedClaims"])

    def test_unknown_readout_is_rejected(self):
        result = evaluate(payload(readoutSeconds=None, globalShear=0.2, foregroundVelocity=1.0,
                                  restrictedToBackground=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.READOUT_TOKEN, result["rejectedClaims"])

    def test_rigid_scene_matching_shear_is_recorded(self):
        result = evaluate(payload(
            foregroundVelocity=1.0,
            restrictedToBackground=False,
            repeat="pan",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_hidden_hallucination_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-vibration"
        result = evaluate(payload(evidenceId=evidence, repeat="vibration"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
