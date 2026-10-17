"""Tests for TC-P160-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="device-variant")
    base.update({
        "inspectable": ["public-kernel"],
        "omittedComponents": ["proprietary-imaging"],
        "missingMarkedUnknown": True,
        "calledCompleteFirmware": False,
        "completenessEvidence": False,
    })
    base.update(overrides)
    return base


class TCP16002(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_unknown_omissions_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["omittedComponents"], ["proprietary-imaging"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "incomplete-source-called-complete-firmware")

    def test_calling_an_incomplete_archive_complete_is_rejected(self):
        result = evaluate(payload(calledCompleteFirmware=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertNotIn(_MODULE.MISSING_NOT_UNKNOWN, result["rejectedClaims"])

    def test_known_missing_components_are_rejected(self):
        result = evaluate(payload(missingMarkedUnknown=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.MISSING_NOT_UNKNOWN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_unstated_inspection_is_rejected(self):
        result = evaluate(payload(inspectable=[], omittedComponents=[], missingMarkedUnknown=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INSPECTION_UNSTATED, result["rejectedClaims"])

    def test_complete_package_with_evidence_is_recorded(self):
        result = evaluate(payload(
            omittedComponents=[],
            calledCompleteFirmware=True,
            completenessEvidence=True,
            missingMarkedUnknown=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc02-software-version"
        result = evaluate(payload(evidenceId=evidence, repeat="software-version"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(inspectable="kernel"))
