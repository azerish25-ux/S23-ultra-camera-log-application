"""Tests for TC-P160-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="acquisition-only")
    base.update({
        "measurement": "acquisition-only",
        "cause": "storage",
        "claimedRestriction": "storage",
        "isolated": True,
        "proposesLowLevelModification": False,
        "assumesVendorBlocking": False,
    })
    base.update(overrides)
    return base


class TCP16001(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_cause_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["cause"], "storage")
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "slow-path-assumed-vendor-blocking")

    def test_assuming_vendor_blocking_is_rejected(self):
        result = evaluate(payload(cause="scheduling", assumesVendorBlocking=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_firmware_claim_for_a_storage_stall_is_rejected(self):
        result = evaluate(payload(claimedRestriction="firmware"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_low_level_modification_without_isolation_is_rejected(self):
        result = evaluate(payload(isolated=False, proposesLowLevelModification=True, measurement="encoder-stage"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ISOLATION_REQUIRED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_deleted_failed_record_is_rejected_inside_the_case(self):
        result = evaluate(payload(records=_GATE.deleted_failed_records()))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DELETED_FAILED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc01-saved-source"
        result = evaluate(payload(evidenceId=evidence, repeat="saved-source", measurement="saved-source"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(measurement="gpu"))
        with self.assertRaises(ValueError):
            evaluate(payload(isolated="yes"))
