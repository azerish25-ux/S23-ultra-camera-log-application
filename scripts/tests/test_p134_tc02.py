"""Tests for TC-P134-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p134_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p134_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p134-tc02",
        "repeat": "preset changes",
        "progress": _GATE.fixture_progress(),
        "sourceId": "1080p-sdr",
        "lookId": "imax-style",
        "virtualFormat": "IMAX 70mm",
        "displayedSourceId": "1080p-sdr",
        "displayedLookId": "imax-style",
        "sourceEvidenceStatus": "measured",
        "lookEvidenceStatus": "simulated",
    }
    base.update(overrides)
    return base


class TCP13402(unittest.TestCase):
    def assert_contract(self, result, evidence="p134-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P134-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_and_look_display_independently(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["displayedSourceId"], "1080p-sdr")
        self.assertEqual(result["preservedResults"][2]["displayedLookId"], "imax-style")
        self.assertIsNone(result["preservedResults"][1]["fraction"])

    def test_renaming_the_source_after_the_virtual_format_is_rejected(self):
        result = evaluate(payload(displayedSourceId="IMAX 70mm", repeat="export sharing"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_qualified_look_evidence_is_rejected(self):
        result = evaluate(payload(lookEvidenceStatus="qualified"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOOK_EVIDENCE_QUALIFIED, result["rejectedClaims"])
        self.assertNotIn(result["decision"], {"qualified", "allowed"})

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p134-tc02-reopen"
        result = evaluate(payload(evidenceId=evidence, repeat="saved recipe reopening"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceId=""))
