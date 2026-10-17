"""Tests for TC-P136-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p136_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p136_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p136-tc02",
        "repeat": "preset",
        "report": _GATE.honest_report(),
        "sourceMode": "1080p SDR",
        "virtualFormat": "IMAX 70mm",
        "displayedSource": "1080p SDR",
        "displayedLook": "IMAX 70mm simulated",
        "lookSimulated": True,
        "sourceEvidence": "source-unqualified",
        "lookEvidence": "look-simulated",
        "renamedSourceAfterFormat": False,
    }
    base.update(overrides)
    return base


class TCP13602(unittest.TestCase):
    def assert_contract(self, result, evidence="p136-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P136-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")
        self.assertTrue(result["reasons"])

    def test_constants(self):
        self.assertEqual(_MODULE.CASE["name"], "Source-look label confusion")
        self.assertEqual(
            _MODULE.CASE["intervention"],
            "Select a large-format film recipe while the underlying source remains a lower-resolution SDR or experimental RAW route.",
        )
        self.assertEqual(
            _MODULE.CASE["expected"],
            "Display the actual source and simulated look independently with their evidence status.",
        )
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Renaming a source mode after the virtual format must fail.",
        )
        self.assertEqual(
            _MODULE.CASE["repeat"],
            "Repeat preset changes, saved recipe reopening, and export sharing.",
        )

    def test_independent_source_and_look_are_recorded_as_not_run(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        view = result["preservedResults"][2]
        self.assertEqual(view["displayedSource"], "1080p SDR")
        self.assertEqual(view["displayedLook"], "IMAX 70mm simulated")
        self.assertFalse(view["renamed"])
        self.assertEqual(result["preservedResults"][1]["status"], "not-run")
        self.assertIsNone(result["preservedResults"][1]["shootingWorkflow"])

    def test_renaming_the_source_after_the_format_is_rejected(self):
        result = evaluate(payload(renamedSourceAfterFormat=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["sourceMode"], "1080p SDR")

    def test_displayed_source_matching_the_virtual_format_is_rejected(self):
        result = evaluate(payload(displayedSource="IMAX 70mm"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NOT_INDEPENDENT, result["rejectedClaims"])

    def test_unlabelled_look_is_rejected(self):
        result = evaluate(payload(lookSimulated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_INDEPENDENT, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_screenshot_approval_is_rejected(self):
        result = evaluate(payload(report=_GATE.honest_report(approved=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DESKTOP_SCREENSHOT_APPROVAL, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p136-tc02-export"
        result = evaluate(payload(evidenceId=evidence, repeat="export", sourceMode="experimental RAW", displayedSource="experimental RAW"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourceMode=""))
