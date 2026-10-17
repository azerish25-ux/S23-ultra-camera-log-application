"""Tests for TC-P135-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p135_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p135_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p135-tc06",
        "repeat": "encoder drain",
        "comparison": _GATE.make_comparison(),
        "progressBannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "encoder-drain",
    }
    base.update(overrides)
    return base


class TCP13506(unittest.TestCase):
    def assert_contract(self, result, evidence="p135-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P135-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_stage_is_recorded_without_a_full_banner(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=encoder-drain", result["preservedResults"])
        self.assertTrue(result["preservedResults"][1]["matchedInputs"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "premature-complete-banner")

    def test_one_hundred_percent_before_verification_is_rejected(self):
        result = evaluate(payload(progressBannerPercent=100, remainingStage="verification"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_completed_gates_can_record_one_hundred_percent(self):
        result = evaluate(payload(
            progressBannerPercent=100,
            verificationComplete=True,
            publicationComplete=True,
            remainingStage=None,
            repeat="gallery commit",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("remainingStage=none", result["preservedResults"])

    def test_a_remaining_stage_blocks_the_complete_banner(self):
        result = evaluate(payload(
            progressBannerPercent=100,
            verificationComplete=True,
            publicationComplete=True,
            remainingStage="synchronized-playback",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(progressBannerPercent=101))
