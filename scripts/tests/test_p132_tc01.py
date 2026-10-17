"""Tests for TC-P132-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p132_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p132_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p132-tc01",
        "repeat": "landscape",
        "scopes": _GATE.fixture_scopes(),
        "source": _GATE.fixture_source(),
        "applyMutant": False,
        "fontScale": 1.6,
        "orientation": "landscape",
        "activeTake": True,
        "recordReachable": True,
        "stopReachable": True,
        "warningsReadable": True,
        "sourceStatusReadable": True,
        "actionsHiddenInScroll": False,
        "sourceStatusText": "sensor_code unclipped",
    }
    base.update(overrides)
    return base


class TCP13201(unittest.TestCase):
    def assert_contract(self, result, evidence="p132-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P132-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reachable_landscape_controls_keep_the_clipping_count(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)
        self.assertEqual(result["preservedResults"][1]["sourceClippingCount"], 0)
        self.assertEqual(result["preservedResults"][1]["staleScopeIds"], ["stale-waveform"])
        self.assertEqual(_MODULE.CASE["name"], "Landscape and large-text stress")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "critical-actions-hidden-in-scrolling-content")

    def test_actions_hidden_in_scroll_are_rejected(self):
        result = evaluate(payload(actionsHiddenInScroll=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["previewClippingCount"], 3)

    def test_source_status_that_hides_the_domain_is_rejected(self):
        result = evaluate(payload(sourceStatusText="display_sdr clipped"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p132-tc01-portrait"
        result = evaluate(payload(evidenceId=evidence, repeat="portrait", orientation="portrait", fontScale=1.0))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(fontScale=0))
            evaluate(payload(applyNegative=True))
