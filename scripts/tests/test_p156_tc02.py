"""Tests for TC-P156-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def package(**overrides):
    value = {
        "name": "public-kernel",
        "inspectable": ["kernel-source", "public-logs"],
        "missing": ["proprietary-imaging"],
        "claimedComplete": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="SM-S911B")
    base.update({"package": package()})
    base.update(overrides)
    return base


class TCP15602(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_incomplete_public_source_is_recorded_as_unknown(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["missing"], ["proprietary-imaging"])
        self.assertFalse(result["preservedResults"][3]["claimedComplete"])
        self.assertEqual(_MODULE.CASE["name"], "Incomplete public source")

    def test_calling_the_archive_complete_is_rejected(self):
        result = evaluate(payload(package=package(claimedComplete=True)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_a_component_cannot_be_both_inspectable_and_missing(self):
        result = evaluate(payload(package=package(
            inspectable=["kernel-source", "proprietary-imaging"],
            missing=["proprietary-imaging"],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNKNOWN_OMITTED, result["rejectedClaims"])

    def test_complete_claim_with_proprietary_imaging_inspected_is_recorded(self):
        result = evaluate(payload(package=package(
            inspectable=["kernel-source", "proprietary-imaging"],
            missing=[],
            claimedComplete=True,
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_empty_stop_conditions_are_rejected_inside_the_case(self):
        result = evaluate(payload(stop_conditions=[]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MISSING_STOP_CONDITIONS, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc02-variant"
        result = evaluate(payload(evidenceId=evidence, repeat="SM-S918B"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(package=package(claimedComplete="yes")))
