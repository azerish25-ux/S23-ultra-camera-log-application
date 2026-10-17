"""Tests for TC-P145-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc04",
        "repeat": "startup",
        "offlineDefault": True,
        "localAssetsInstalled": True,
        "transmissions": [],
        "observation": "startup",
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14504(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Unexpected network transmission")
        self.assertEqual(
            _MODULE.CASE["negative"],
            "An analytics thumbnail upload contradicts the local-processing claim.",
        )

    def test_offline_default_with_no_traffic_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["transmitted"], [])

    def test_frames_depth_audio_and_metadata_are_rejected(self):
        for kind in ("frames", "depth", "audio", "private-metadata"):
            result = evaluate(payload(
                observation="export",
                repeat="export",
                transmissions=[{"kind": kind, "bytes": 32, "when": "export"}],
            ))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "rejected", kind)
            self.assertIn(_MODULE.OFFLINE_TRANSMISSION, result["rejectedClaims"])
            self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_analytics_thumbnail_is_rejected(self):
        result = evaluate(payload(
            observation="model-initialization",
            repeat="model-initialization",
            transmissions=[{"kind": "analytics-thumbnail", "bytes": 12, "when": "startup"}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_zero_byte_observation_is_not_a_transmission(self):
        result = evaluate(payload(
            observation="errors",
            repeat="errors",
            transmissions=[{"kind": "frames", "bytes": 0, "when": "errors"}],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_disabling_the_offline_default_is_rejected(self):
        result = evaluate(payload(offlineDefault=False, observation="crashes", repeat="crashes"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OFFLINE_DISABLED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc04-crashes"
        result = evaluate(payload(evidenceId=evidence, observation="crashes", repeat="crashes"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(transmissions=[{"kind": "pixels", "bytes": 1, "when": "startup"}]))
