"""Tests for TC-P132-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc06",
        "repeat": "encoder drain",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "progressBannerPercent": 40,
        "verificationComplete": False,
        "publicationComplete": False,
        "remainingStage": "verification",
    }
    base.update(overrides)
    return base


class TCP13206(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_stage_is_recorded_without_a_complete_banner(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remainingStage=verification", result["preservedResults"])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_one_hundred_percent_before_verification_is_rejected(self):
        result = evaluate(payload(progressBannerPercent=100))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_complete_gates_can_clear_the_banner(self):
        result = evaluate(payload(
            progressBannerPercent=100,
            verificationComplete=True,
            publicationComplete=True,
            remainingStage=None,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("remainingStage=none", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(remainingStage="done"))
        with self.assertRaises(ValueError):
            evaluate(payload(progressBannerPercent=101))
