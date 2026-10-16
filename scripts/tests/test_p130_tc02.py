"""Tests for TC-P130-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p130_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p130_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p130-tc02",
        "repeat": "preset",
        "committed": _GATE.make_selection(),
        "proposed": _GATE.imax_proposal(),
        "displayedSourceId": _GATE.FIXTURE_SOURCE_ID,
        "displayedLookId": _GATE.FIXTURE_LOOK_ID,
        "displayedTransfer": "bt709",
        "sourceEvidenceStatus": "labelled-source-mode",
        "lookEvidenceStatus": "simulated",
    }
    base.update(overrides)
    return base


class TCP13002(unittest.TestCase):
    def assert_contract(self, result, evidence="p130-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P130-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_source_and_look_display_independently(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["source_transfer"], "bt709")
        self.assertEqual(record["look_id"], "imax-style-simulated")
        self.assertNotEqual(record["source_id"], record["look_id"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "renamed-source-mode-after-virtual-format")

    def test_renaming_the_source_after_the_virtual_format_is_rejected(self):
        proposed = _GATE.imax_proposal(source_id="IMAX 70mm", recording_mode="IMAX 70mm")
        result = evaluate(payload(
            proposed=proposed,
            displayedSourceId="IMAX 70mm",
            displayedTransfer="logc3",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.LOOK_ALTERED_SOURCE, result["rejectedClaims"])
        self.assertIn(_GATE.RENAMED_IMAX_70MM, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["source_id"], _GATE.FIXTURE_SOURCE_ID)
        self.assertEqual(result["preservedResults"][1]["source_sha256"], _GATE.FIXTURE_SOURCE_SHA256)
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_log_recipe_cannot_relabel_the_displayed_transfer(self):
        proposed = _GATE.make_selection(
            look_id="LogC3",
            look_params={"curve": "print"},
            source_transfer="logc3",
        )
        result = evaluate(payload(
            proposed=proposed,
            displayedLookId="LogC3",
            displayedTransfer="bt709",
            lookEvidenceStatus="simulated",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.LOOK_RELABELLED_LOGC3, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["source_transfer"], "bt709")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p130-tc02-reopen"
        result = evaluate(payload(evidenceId=evidence, repeat="saved recipe reopening"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(displayedSourceId=""))
