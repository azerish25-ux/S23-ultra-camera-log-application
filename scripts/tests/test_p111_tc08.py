"""Tests for TC-P111-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat blinded presentation, moderate blur, aggressive blur, and held-out scenes.",
        "releaseRequested": False,
        "frames": [
            {"id": "f0", "score": 0.98, "catastrophic": False},
            {"id": "f1", "score": 0.97, "catastrophic": False},
            {"id": "f2", "score": 0.99, "catastrophic": True},
        ],
    }
    base.update(overrides)
    return base


class TCP11108(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(str(item).startswith("catastrophic:") for item in result["preservedResults"]))
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_catastrophic_frames_are_recorded_and_release_stays_limited(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("catastrophic:f2", result["preservedResults"])
        self.assertTrue(any(item.startswith("mean_score:") for item in result["preservedResults"]))
        self.assertTrue(any("mean_score=" in item for item in result["reasons"]))

    def test_favorable_mean_cannot_authorize_release(self):
        result = evaluate(payload(releaseRequested=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mean-score-hides-severe-boundary-failures", result["rejectedClaims"])
        self.assertIn("catastrophic:f2", result["preservedResults"])
        joined = " ".join(result["reasons"])
        self.assertIn("0.98", joined)

    def test_clean_clip_can_be_recorded(self):
        frames = [
            {"id": "a", "score": 0.9, "catastrophic": False},
            {"id": "b", "score": 0.8, "catastrophic": False},
        ]
        result = evaluate(payload(frames=frames, releaseRequested=True, evidenceId="p111-held-out", repeat="held-out scenes"))
        self.assert_contract(result, "p111-held-out")
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("catastrophic:none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[{"id": "a", "score": 1.2, "catastrophic": False}, {"id": "b", "score": 0.2, "catastrophic": False}]))
