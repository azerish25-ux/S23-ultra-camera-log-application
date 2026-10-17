"""Tests for TC-P131-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p131_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p131_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p131-tc02",
        "repeat": "preset",
        "committed": _GATE.make_control(),
        "proposed": _GATE.held_proposal(),
        "displayedSource": _GATE.FIXTURE_SOURCE,
        "displayedLook": "large-format-simulated",
        "displayedUnit": "deg",
        "sourceEvidenceStatus": "host-reference",
        "lookEvidenceStatus": "simulated",
    }
    base.update(overrides)
    return base


class TCP13102(unittest.TestCase):
    def assert_contract(self, result, evidence="p131-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P131-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_and_look_display_independently(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)
        self.assertEqual(result["preservedResults"][1]["applied"], 180)
        self.assertEqual(result["preservedResults"][1]["draft"], "1.")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "renamed-source-mode-after-virtual-format")

    def test_renaming_the_source_after_the_virtual_format_is_rejected(self):
        result = evaluate(payload(displayedSource="IMAX 70mm"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["source_configuration"], _GATE.FIXTURE_SOURCE)
        self.assertEqual(result["preservedResults"][1]["applied"], 180)

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p131-tc02-export"
        result = evaluate(payload(evidenceId=evidence, repeat="export"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(displayedSource=""))
