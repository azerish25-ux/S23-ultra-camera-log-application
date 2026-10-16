"""Tests for TC-P116-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p116_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p116_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def transform(**overrides):
    value = {"scale": 1.0, "rotationRadians": 0.0, "tx": 0.1, "ty": -0.2}
    value.update(overrides)
    return value


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
        "rgbTransform": transform(),
        "depthTransform": transform(),
        "maskTransform": transform(),
        "sourceFovDegrees": 60.0,
        "reportedFovDegrees": 60.0,
        "sourceValidArea": 1.0,
        "reportedValidArea": 1.0,
    }
    base.update(timeline())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP11605(unittest.TestCase):
    def assert_contract(self, result, evidence="p116-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P116-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("interpolationFraction=1/3=0.3333333333333333", blob(result))

    def test_shared_transform_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("origin=estimated t=0.5 value=1", result["preservedResults"])

    def test_unchanged_mask_is_rejected(self):
        result = evaluate(payload(maskTransform=transform(tx=0.0)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_depth_left_behind_is_rejected(self):
        result = evaluate(payload(depthTransform=transform(tx=0.0, ty=0.0)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DEPTH_TOKEN, result["rejectedClaims"])

    def test_crop_updates_fov_and_valid_area(self):
        cropped = transform(scale=2.0, rotationRadians=1.5707963267948966)
        result = evaluate(payload(
            rgbTransform=cropped,
            depthTransform=cropped,
            maskTransform=cropped,
            reportedFovDegrees=30.0,
            reportedValidArea=0.25,
            repeat="portrait",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_stale_fov_is_rejected(self):
        cropped = transform(scale=2.0)
        result = evaluate(payload(
            rgbTransform=cropped,
            depthTransform=cropped,
            maskTransform=cropped,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FOV_TOKEN, result["rejectedClaims"])

    def test_hidden_hallucination_is_rejected(self):
        result = evaluate(payload(**timeline(
            estimated=[{"time": 0.5, "value": 1.0, "origin": "captured"}],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("hidden-hallucination", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p116-crop"
        result = evaluate(payload(evidenceId=evidence, repeat="crop"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
