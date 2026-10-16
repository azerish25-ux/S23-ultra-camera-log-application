"""Tests for TC-P118-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
ROWS = [
    {"rowIndex": 0, "y": 10.0, "velocityY": 4.0, "role": "background"},
    {"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "background"},
    {"rowIndex": 1, "y": 8.0, "velocityY": -2.0, "role": "foreground"},
]


def payload(**overrides):
    base = {
        "evidenceId": "p118-rolling",
        "repeat": "moving-subject",
        "advertisedUniversal": False,
        "readoutSecondsPerRow": 0.5,
        "readoutSource": "measured",
        "cameraVelocityY": 4.0,
        "warpLabel": "rolling_shutter_correction",
        "claimsGlobalShutterRestored": False,
        "rows": ROWS,
    }
    base.update(overrides)
    return base


class TCP11806(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-rolling"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Rolling-shutter model violation")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Place independently moving foreground content in a scene used for global camera-motion correction.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Restrict or qualify the correction rather than applying an unjustified global warp to every object.",
        )
        self.assertEqual(
            _MODULE.NEGATIVE,
            "One global shear must not be advertised as universal rolling-shutter removal.",
        )
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat pans, vibrations, moving subjects, and unknown readout timing.",
        )

    def test_measured_per_row_correction_reports_shift_and_residual(self):
        result = evaluate(payload(repeat="pan"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("correction_applied true", result["preservedResults"])
        self.assertIn("maxRowShiftPixels=4", result["preservedResults"])
        self.assertIn("residualErrorPixels=3", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [10.0, 20.0, 8.0])
        self.assertEqual(result["preservedResults"][5], [10.0, 24.0, 7.0])
        self.assertEqual(result["preservedResults"][6], [0.0, 4.0, -1.0])
        self.assertEqual(result["preservedResults"][7], [0.0, 1.0, 0.5])

    def test_global_shear_does_not_warp_the_person(self):
        result = evaluate(payload(warpLabel="global_camera_shear", repeat="vibration"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unjustified-global-camera-warp-of-foreground", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][5], [10.0, 24.0, 8.0])
        self.assertEqual(result["preservedResults"][6], [0.0, 4.0, 0.0])
        self.assertNotEqual(result["preservedResults"][5][2], 10.0)

    def test_universal_advertisement_is_rejected(self):
        result = evaluate(payload(advertisedUniversal=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p118-rolling", result["preservedResults"])

    def test_unknown_readout_refuses_the_labelled_warp(self):
        result = evaluate(
            payload(
                readoutSecondsPerRow=None,
                readoutSource=None,
                warpLabel="rolling_shutter_correction",
                repeat="unknown-readout",
                rows=[{"rowIndex": 2, "y": 20.0, "velocityY": 4.0, "role": "background"}],
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("rolling-shutter-correction-without-measured-readout", result["rejectedClaims"])
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertIn("maxRowShiftPixels=0", result["preservedResults"])
        self.assertEqual(result["preservedResults"][5], [20.0])
        self.assertEqual(result["preservedResults"][6], [0.0])
        self.assertEqual(result["preservedResults"][7], [None])

    def test_global_shutter_claim_is_rejected(self):
        result = evaluate(payload(claimsGlobalShutterRestored=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction-restores-global-shutter", result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][5], [10.0, 24.0, 7.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(readoutSecondsPerRow=float("inf")))
