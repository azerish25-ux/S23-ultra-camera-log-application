"""Tests for TC-P118-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p118_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p118_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def transform(scale=2.0, rotation=0.0, tx=0.0, ty=1.0):
    return {"scale": scale, "rotationRadians": rotation, "tx": tx, "ty": ty}


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
    shared = transform()
    base = {
        "evidenceId": "p118-stab",
        "repeat": "crop",
        "rgbTransform": shared,
        "depthTransform": dict(shared),
        "maskTransform": dict(shared),
        "sourceFovDegrees": 40.0,
        "reportedFovDegrees": 20.0,
        "sourceValidArea": 100.0,
        "reportedValidArea": 25.0,
    }
    base.update(correction())
    base.update(overrides)
    return base


class TCP11805(unittest.TestCase):
    def assert_contract(self, result, evidence="p118-stab"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P118-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Stabilization-depth misalignment")
        self.assertEqual(
            _MODULE.NEGATIVE,
            "Stabilizing color alone while leaving masks unchanged must fail.",
        )

    def test_shared_transform_updates_fov_and_area(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("shared stabilization transform updated fov and valid area", result["reasons"])

    def test_mask_and_depth_left_behind_are_rejected(self):
        result = evaluate(
            payload(
                maskTransform=transform(scale=1.0),
                depthTransform=transform(tx=4.0),
                repeat="portrait",
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.DEPTH_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_stale_fov_is_rejected(self):
        result = evaluate(payload(reportedFovDegrees=40.0, reportedValidArea=100.0))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOV_TOKEN, result["rejectedClaims"])
        blob = " ".join(result["reasons"])
        self.assertIn("expectedFov=20", blob)
        self.assertIn("expectedValidArea=25", blob)

    def test_unknown_readout_warp_does_not_shift_rows(self):
        result = evaluate(
            payload(
                **correction(
                    warpLabel="rolling_shutter_correction",
                    rows=[{"rowIndex": 2, "y": 9.0, "velocityY": 1.0, "role": "background"}],
                )
            )
        )
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("correction_applied false", result["preservedResults"])
        self.assertEqual(result["preservedResults"][4], [9.0])
        self.assertEqual(result["preservedResults"][5], [0.0])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(rgbTransform=transform(scale=0.0)))
