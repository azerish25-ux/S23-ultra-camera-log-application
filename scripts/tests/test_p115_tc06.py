"""Tests for TC-P115-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p115_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p115_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p115-rolling",
        "independentForeground": True,
        "correction": "restricted",
        "advertisedUniversal": False,
        "readoutKnown": True,
        "repeat": "moving-subject",
    }
    base.update(overrides)
    return base


class TCP11506(unittest.TestCase):
    def assert_contract(self, result, evidence="p115-rolling"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P115-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Rolling-shutter model violation")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "One global shear must not be advertised as universal rolling-shutter removal.",
        )
        self.assertIn("unknown readout timing", _MODULE.REPEAT)

    def test_restricted_correction_is_recorded(self):
        result = evaluate(payload(repeat="pan"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("correction:restricted", result["preservedResults"])

    def test_global_shear_on_foreground_is_rejected(self):
        result = evaluate(payload(correction="global-shear", repeat="vibration"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unjustified-global-warp", result["rejectedClaims"])
        self.assertIn("correction:global-shear", result["preservedResults"])

    def test_universal_advertisement_and_unknown_readout_are_rejected(self):
        advertised = evaluate(payload(advertisedUniversal=True))
        self.assertEqual(advertised["decision"], "rejected")
        self.assertIn("global-shear-as-universal-rolling-shutter-removal", advertised["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, advertised["reasons"])
        unknown = evaluate(
            payload(
                independentForeground=False,
                correction="global-shear",
                readoutKnown=False,
                repeat="unknown-readout",
            )
        )
        self.assertEqual(unknown["decision"], "rejected")
        self.assertIn("unknown-readout-global-warp", unknown["rejectedClaims"])
        clean = evaluate(
            payload(
                evidenceId="p115-global-ok",
                independentForeground=False,
                correction="global-shear",
                readoutKnown=True,
                repeat="pan",
            )
        )
        self.assert_contract(clean, "p115-global-ok")
        self.assertEqual(clean["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(correction="magic"))
