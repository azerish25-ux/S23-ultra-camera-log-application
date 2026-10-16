"""Tests for TC-P118-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def correction(**overrides):
    value = {
        "readoutSecondsPerRow": None,
        "readoutSource": None,
        "cameraVelocityY": 0.0,
        "warpLabel": "none",
        "claimsGlobalShutterRestored": False,
        "rows": [{"rowIndex": 0, "y": 1.0, "velocityY": 0.0, "role": "background"}],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p118-blur",
        "repeat": "short-exposure",
        "sourceBlurSeconds": 0.01,
        "targetExposureSeconds": 0.04,
        "claimsExactArbitraryConversion": False,
        "thinMotionUndersampled": False,
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11802(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-blur"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Existing blur ambiguity")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Claiming exact arbitrary shutter conversion from any source must fail.",
        )
        self.assertIn("undersampled thin motion", _MODULE.REPEAT)

    def test_qualified_additional_blur_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("qualifiedAdditionalBlurSeconds=0.03", result["reasons"])
        kept = next(item for item in result["preservedResults"] if isinstance(item, dict))
        self.assertEqual(kept["sourceBlurSeconds"], 0.01)
        self.assertEqual(kept["targetExposureSeconds"], 0.04)

    def test_exact_conversion_and_existing_blur_are_rejected(self):
        exact = evaluate(payload(claimsExactArbitraryConversion=True, repeat="long-exposure"))
        self.assertEqual(exact["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, exact["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, exact["reasons"])
        longer = evaluate(payload(sourceBlurSeconds=0.05, targetExposureSeconds=0.01))
        self.assertEqual(longer["decision"], "rejected")
        self.assertIn(_MODULE.CANNOT_RECONSTRUCT, longer["rejectedClaims"])
        self.assertIn("qualifiedAdditionalBlurSeconds=0", longer["reasons"])
        self.assertNotIn("qualifiedAdditionalBlurSeconds=-0.04", " ".join(longer["reasons"]))

    def test_undersampled_thin_motion_is_rejected(self):
        result = evaluate(payload(thinMotionUndersampled=True, repeat="undersampled-thin"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDERSAMPLED, result["rejectedClaims"])

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 3, "y": 4.0, "velocityY": 2.0, "role": "foreground"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [4.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceBlurSeconds=-1))
