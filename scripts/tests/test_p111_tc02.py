"""Tests for TC-P111-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat thin objects, hands, hair, and large foreground occluders.",
        "revealed": [
            {"id": "hair-1", "fill": "current_evidence"},
            {"id": "hand-2", "fill": "uncertain"},
        ],
    }
    base.update(overrides)
    return base


class TCP11102(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_current_evidence_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("old_depth:0", result["preservedResults"])
        self.assertIn("current_evidence:1", result["preservedResults"])
        self.assertIn("uncertain:1", result["preservedResults"])

    def test_old_depth_fill_is_rejected(self):
        revealed = [
            {"id": "bg-1", "fill": "old_depth"},
            {"id": "bg-2", "fill": "old_depth"},
            {"id": "bg-3", "fill": "current_evidence"},
        ]
        result = evaluate(payload(revealed=revealed))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("old-depth-fill-on-disocclusion", result["rejectedClaims"])
        self.assertIn("old_depth:2", result["preservedResults"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        result = evaluate(payload(evidenceId="p111-hair", repeat="hair"))
        self.assert_contract(result, "p111-hair")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(revealed=[{"id": "a", "fill": "copied"}]))
