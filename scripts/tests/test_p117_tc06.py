"""Tests for TC-P117-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p117_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p117_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def geometry(**overrides):
    value = _MODULE._CORE.recorded_geometry()
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p117-shear",
        "repeat": "moving-subjects",
        "foregroundVelocity": 3.0,
        "backgroundVelocity": 1.0,
        "globalShear": 0.02,
        "readoutSeconds": 0.02,
        "advertisedUniversal": False,
        "restrictedToBackground": True,
        "geometry": geometry(),
    }
    base.update(overrides)
    return base


def blob(result):
    return " ".join(str(item) for item in result["reasons"] + result["preservedResults"])


class TCP11706(unittest.TestCase):
    def assert_contract(self, result, evidence="p117-shear"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P117-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("cropCoverage=6/8=0.75", blob(result))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Rolling-shutter model violation")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "One global shear must not be advertised as universal rolling-shutter removal.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat pans, vibrations, moving subjects, and unknown readout timing.",
        )

    def test_background_only_shear_is_recorded(self):
        self.assertEqual(_MODULE.background_shear(1.0, 0.02), 0.02)
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("expectedBackgroundShear=0.02", result["preservedResults"])

    def test_universal_claim_is_rejected(self):
        result = evaluate(payload(advertisedUniversal=True, repeat="pans"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_foreground_included_in_the_global_warp_is_rejected(self):
        result = evaluate(payload(restrictedToBackground=False, repeat="vibrations"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.WARP_TOKEN, result["rejectedClaims"])

    def test_unknown_readout_cannot_justify_a_shear(self):
        result = evaluate(payload(readoutSeconds=None, globalShear=0.2, repeat="unknown-readout"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.READOUT_TOKEN, result["rejectedClaims"])

    def test_shear_that_does_not_match_background_readout_is_rejected(self):
        result = evaluate(payload(globalShear=0.5))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SHEAR_TOKEN, result["rejectedClaims"])
        self.assertIn("expectedBackgroundShear=0.02", result["preservedResults"])

    def test_generated_fill_is_rejected_for_a_restricted_shear(self):
        result = evaluate(payload(geometry=geometry(fill="generated")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("generated-fill", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
