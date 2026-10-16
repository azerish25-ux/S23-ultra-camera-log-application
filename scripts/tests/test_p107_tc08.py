"""Tests for TC-P107-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "moderate-blur",
        "frame_scores": [0.95, 0.96, 0.94, 0.97],
        "severe_boundary_failures": 0,
        "severe_recorded_separately": False,
        "release_limited": False,
        "selected_best_frames_only": False,
    }
    base.update(overrides)
    return base


class TCP10708(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_clean_clip_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("severe=0", result["preservedResults"])
        self.assertTrue(any(item.startswith("mean=") for item in result["preservedResults"]))

    def test_favorable_mean_cannot_hide_severe_failures(self):
        result = evaluate(payload(severe_boundary_failures=2))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mean-hides-severe-failures", result["rejectedClaims"])
        self.assertIn("release-not-limited", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("severe=2", result["preservedResults"])

    def test_separated_failures_with_limited_release_are_recorded(self):
        evidence = "p107-aggressive"
        result = evaluate(
            payload(
                evidenceId=evidence,
                severe_boundary_failures=2,
                severe_recorded_separately=True,
                release_limited=True,
            )
        )
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("severe=2", result["preservedResults"])

    def test_best_frames_only_is_rejected(self):
        result = evaluate(payload(selected_best_frames_only=True))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("best-frames-only", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(frame_scores=[]))
        with self.assertRaises(ValueError):
            evaluate({})
