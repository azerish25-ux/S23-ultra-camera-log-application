"""Tests for TC-P110-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p110_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p110_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p110-evidence",
        "repeat": "Repeat brief occlusion",
        "frames": [
            {"candidates": [{"id": "a", "distance": 2.0}, {"id": "b", "distance": 3.0}]},
            {"candidates": [{"id": "a", "distance": 2.5}, {"id": "b", "distance": 1.0}]},
        ],
        "targetId": "a",
        "policy": "identity",
    }
    base.update(overrides)
    return base


class TCP11006(unittest.TestCase):
    def assert_contract(self, result, evidence="p110-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P110-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_identity_policy_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("chosen a,a", result["reasons"])

    def test_target_loss_holds_identity(self):
        frames = [
            {"candidates": [{"id": "a", "distance": 2.0}, {"id": "b", "distance": 2.4}]},
            {"candidates": [{"id": "b", "distance": 1.0}]},
        ]
        result = evaluate(payload(frames=frames))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("chosen a,a", result["reasons"])

    def test_nearest_face_each_frame_is_rejected(self):
        result = evaluate(payload(policy="nearest-face"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-face-independently-each-frame", result["rejectedClaims"])
        self.assertIn("chosen a,b", result["reasons"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
