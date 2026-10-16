"""Tests for TC-P124-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "exportedPaths": ["bundle/clip.mov", "bundle/interpretation.json"],
        "kind": "log",
        "interpretationRecordPresent": True,
        "presentedAsSelfDescribing": False,
        "technicalInterpretationRetained": True,
    }
    base.update(overrides)
    return base


class TCP12408(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_log_with_interpretation_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("interpretation-record", result["preservedResults"])

    def test_log_without_interpretation_is_not_self_describing(self):
        result = evaluate(payload(interpretationRecordPresent=False, presentedAsSelfDescribing=True,
                                  technicalInterpretationRetained=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.LOG_WITHOUT, result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_private_paths_are_rejected_and_not_preserved_as_exports(self):
        result = evaluate(payload(exportedPaths=["/sdcard/DCIM/private.mov", "bundle/interpretation.json"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PRIVATE_PATH, result["rejectedClaims"])
        self.assertNotIn("path=/sdcard/DCIM/private.mov", result["preservedResults"])
        self.assertIn("path=bundle/interpretation.json", result["preservedResults"])

    def test_sdr_hdr_and_partial_repeats(self):
        sdr = evaluate(payload(kind="sdr", interpretationRecordPresent=False, presentedAsSelfDescribing=True))
        self.assertEqual(sdr["decision"], "recorded")
        hdr = evaluate(payload(kind="hdr-derived", interpretationRecordPresent=False))
        self.assertEqual(hdr["decision"], "rejected")
        self.assertIn(_MODULE.HDR_WITHOUT, hdr["rejectedClaims"])
        partial = evaluate(payload(kind="unverified-partial", presentedAsSelfDescribing=True))
        self.assertEqual(partial["decision"], "rejected")
        self.assertIn(_MODULE.PARTIAL, partial["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-sdr"
        result = evaluate(payload(evidenceId=evidence, repeat="sdr", kind="sdr"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
