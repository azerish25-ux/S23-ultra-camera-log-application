"""Tests for TC-P156-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p156_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p156_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def stages():
    return [
        {"id": "acquire", "domain": "acquisition-only", "cause": "measured", "isolated": True, "slow": False},
        {"id": "saved", "domain": "saved-source", "cause": "storage", "isolated": True, "slow": True},
        {"id": "develop", "domain": "development", "cause": "measured", "isolated": True, "slow": False},
        {"id": "encode", "domain": "encoder-stage", "cause": "scheduling", "isolated": True, "slow": True},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="acquisition-only")
    base.update({"stages": stages(), "proposeFirmwareChange": False})
    base.update(overrides)
    return base


class TCP15601(unittest.TestCase):
    def assert_contract(self, result, evidence="p156-firmware-risk-gate"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P156-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])
        self.assertFalse(result["preservedResults"][1]["flashAuthorized"])

    def test_isolated_storage_and_scheduling_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["isolatedSlow"], ["saved", "encode"])
        self.assertFalse(result["preservedResults"][3]["proposeFirmwareChange"])
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "slow-path-assumed-vendor-blocking")

    def test_assuming_vendor_blocking_without_isolation_is_rejected(self):
        rows = stages()
        rows[1] = {"id": "saved", "domain": "saved-source", "cause": "vendor-blocking", "isolated": False, "slow": True}
        result = evaluate(payload(stages=rows))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_firmware_change_before_isolation_is_rejected(self):
        rows = stages()
        rows[3] = {"id": "encode", "domain": "encoder-stage", "cause": "scheduling", "isolated": False, "slow": True}
        result = evaluate(payload(stages=rows, proposeFirmwareChange=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_ISOLATED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_similar_name_only_is_still_rejected_inside_the_case(self):
        result = evaluate(payload(similar_name_only=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.SIMILAR_NAME_ONLY, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p156-tc01-encoder"
        result = evaluate(payload(evidenceId=evidence, repeat="encoder-stage"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(stages=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(proposeFirmwareChange="yes"))
