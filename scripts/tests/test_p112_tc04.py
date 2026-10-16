"""Tests for TC-P112-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frames(reset_cut=True):
    return [
        {"timestamp_s": 0.0, "scene_id": "shot-a", "carried_history_scene": "shot-a"},
        {"timestamp_s": 1.0 / 24.0, "scene_id": "shot-a", "carried_history_scene": "shot-a"},
        {
            "timestamp_s": 2.0 / 24.0,
            "scene_id": "shot-b",
            "carried_history_scene": "reset" if reset_cut else "shot-a",
        },
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc04",
        "repeat": "hard-cut",
        "frames": frames(True),
    }
    base.update(overrides)
    return base


class TCP11204(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])

    def test_reset_at_cut_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_continuous_clock_across_a_cut_is_rejected(self):
        result = evaluate(payload(frames=frames(False)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(
            "continuous-timestamps-preserved-temporal-state-across-cut",
            result["rejectedClaims"],
        )

    def test_second_evidence_id_is_preserved(self):
        evidence = "p112-tc04-fade"
        result = evaluate(payload(evidenceId=evidence, repeat="fade"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        broken = frames(True)
        broken[2]["timestamp_s"] = broken[1]["timestamp_s"]
        with self.assertRaises(ValueError):
            evaluate(payload(frames=broken))
