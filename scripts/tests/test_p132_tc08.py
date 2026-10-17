"""Tests for TC-P132-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc08",
        "repeat": "one-handed operation",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "physicalObserved": False,
        "desktopMockupSubstituted": False,
        "savedStateDisclosed": True,
        "interruption": "thermal",
        "nextAction": "keep the retained display-domain clipping count and retry the take",
    }
    base.update(overrides)
    return base


class TCP13208(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_disclosed_saved_scopes_are_recorded_without_claiming_the_phone(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)
        self.assertEqual(result["preservedResults"][1]["staleScopeIds"], ["stale-waveform"])
        self.assertEqual(result["preservedResults"][2]["sourceDomain"], "sensor_code")

    def test_desktop_mockup_cannot_substitute(self):
        result = evaluate(payload(desktopMockupSubstituted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_claiming_physical_observation_is_rejected(self):
        result = evaluate(payload(physicalObserved=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNOBSERVED, result["rejectedClaims"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_hidden_saved_state_is_rejected_but_counts_remain(self):
        result = evaluate(payload(savedStateDisclosed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.HIDDEN_SAVE, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(interruption="battery"))
