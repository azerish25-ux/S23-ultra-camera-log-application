"""Tests for TC-P132-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def side(**overrides):
    value = {"scale": 1, "transfer": "display_sdr", "enhanced": False, "time": 0}
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc07",
        "repeat": "source-versus-result",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "left": side(transfer="display_sdr"),
        "right": side(transfer="sensor_code"),
        "mismatchDisclosed": True,
        "preferenceJudgment": True,
    }
    base.update(overrides)
    return base


class TCP13207(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_domain_mismatch_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["mismatch"])
        self.assertEqual(result["preservedResults"][2]["histogramDomain"], "display_sdr")
        self.assertEqual(result["preservedResults"][2]["sourceDomain"], "sensor_code")
        self.assertEqual(result["preservedResults"][2]["previewClippingCount"], 3)
        self.assertEqual(result["preservedResults"][2]["sourceClippingCount"], 0)

    def test_undisclosed_preference_is_rejected(self):
        result = evaluate(payload(mismatchDisclosed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNDISCLOSED, result["rejectedClaims"])
        self.assertIn("p132-tc07", result["preservedResults"])

    def test_auto_enhanced_side_is_rejected(self):
        result = evaluate(payload(left=side(transfer="display_sdr", enhanced=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_renamed_comparison_domain_is_rejected(self):
        result = evaluate(payload(left=side(transfer="sensor_code"), right=side(transfer="sensor_code")))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DOMAIN_MISMATCH, result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(left=side(scale=0)))
