"""Tests for TC-P130-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc06",
        "repeat": "encoder drain",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "progressBannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "verification",
    }
    base.update(overrides)
    return base


class TCP13006(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_gate_shows_the_remaining_stage(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=verification", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "premature-complete-banner")

    def test_one_hundred_percent_before_verification_is_rejected(self):
        result = evaluate(payload(progressBannerPercent=100, repeat="gallery commit"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("remainingStage=verification", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")

    def test_finished_gates_are_recorded_not_qualified(self):
        result = evaluate(payload(
            progressBannerPercent=100,
            verificationComplete=True,
            publicationComplete=True,
            remainingStage=None,
            repeat="sidecar export",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn("remainingStage=none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(progressBannerPercent=101))
        with self.assertRaises(ValueError):
            evaluate(payload(remainingStage="done"))
