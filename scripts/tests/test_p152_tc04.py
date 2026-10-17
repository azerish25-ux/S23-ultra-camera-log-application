"""Tests for TC-P152-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p152_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p152_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="startup")
    base.update({"offlineDefault": True, "transmissions": []})
    base.update(overrides)
    return base


class TCP15204(unittest.TestCase):
    def assert_contract(self, result, evidence="p152-production-readiness"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P152-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_offline_silence_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["bytes"], 0)
        self.assertEqual(_MODULE.CASE["name"], "Unexpected network transmission")

    def test_analytics_thumbnail_is_rejected(self):
        result = evaluate(payload(transmissions=[{
            "kind": "thumbnail",
            "bytes": 128,
            "endpoint": "https://analytics.example/upload",
        }]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_private_frames_under_offline_default_are_rejected(self):
        result = evaluate(payload(transmissions=[{
            "kind": "frames",
            "bytes": 10,
            "endpoint": "https://example/upload",
        }]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_TRANSMISSION, result["rejectedClaims"])

    def test_disabling_offline_default_is_rejected(self):
        result = evaluate(payload(offlineDefault=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_DISABLED, result["rejectedClaims"])

    def test_promotional_evidence_in_the_dossier_is_rejected(self):
        evidence = _GATE.fixture_evidence() + [{"id": "promo-reel", "kind": "promotional-footage"}]
        result = evaluate(payload(evidence=evidence))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PROMOTIONAL_FOOTAGE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p152-tc04-export"
        result = evaluate(payload(evidenceId=evidence, repeat="export"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(transmissions=[{"kind": "frames", "bytes": -1, "endpoint": "local"}]))
