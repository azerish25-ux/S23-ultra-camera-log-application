"""Tests for TC-P155-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def package(**overrides):
    value = {
        "inspectable": ["kernel-source", "public-logs"],
        "missing": ["proprietary-imaging-component"],
        "claimedCompleteCameraFirmware": False,
        "deviceVariant": "SM-S911B",
        "softwareVersion": "S911BXXU3AWF7",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="SM-S911B")
    base.update({"sourcePackage": package()})
    base.update(overrides)
    return base


class TCP15502(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_missing_imaging_component_stays_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertEqual(preserved["missingUnknown"], ["proprietary-imaging-component"])
        self.assertEqual(preserved["inspectable"], ["kernel-source", "public-logs"])
        self.assertFalse(preserved["claimedCompleteCameraFirmware"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")

    def test_calling_the_archive_complete_is_rejected(self):
        result = evaluate(payload(sourcePackage=package(claimedCompleteCameraFirmware=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(
            result["preservedResults"][3]["missingUnknown"],
            ["proprietary-imaging-component"],
        )

    def test_empty_inspectable_surface_is_rejected(self):
        result = evaluate(payload(sourcePackage=package(inspectable=[], missing=[])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOTHING_INSPECTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_completeness_without_a_missing_list_is_still_rejected(self):
        result = evaluate(payload(sourcePackage=package(missing=[], claimedCompleteCameraFirmware=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc02-variant"
        result = evaluate(payload(evidenceId=evidence, repeat="software-version"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(sourcePackage=package(deviceVariant="")))
        with self.assertRaises(ValueError):
            evaluate(payload(sourcePackage={"inspectable": ["kernel-source"]}))
