"""Tests for TC-P122-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc07",
        "repeat": "Repeat fractional rates, audio-bearing clips, and scene cuts at boundaries.",
        "intendedFrames": [0, 1, 2, 3],
        "assembledFrames": [0, 1, 2, 3],
        "playable": True,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12207(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc07"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_exact_timeline_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("intendedCount=4", result["preservedResults"])
        self.assertIn("assembledCount=4", result["preservedResults"])

    def test_duplicated_overlap_is_rejected(self):
        result = evaluate(payload(assembledFrames=[0, 1, 2, 2, 3]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_omitted_boundary_frame_is_rejected(self):
        result = evaluate(payload(assembledFrames=[0, 1, 3], playable=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OMITTED_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_reordered_timeline_is_rejected(self):
        result = evaluate(payload(assembledFrames=[0, 2, 1, 3]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ORDER_TOKEN, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[1]["version_sha256"] = "1" * 64
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc07-fractional"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional rates"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(assembledFrames=[]))
