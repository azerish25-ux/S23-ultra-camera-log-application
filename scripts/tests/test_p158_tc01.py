"""Tests for TC-P158-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p158_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p158_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    return _MODULE.case_payload(**overrides)


class TCP15801(unittest.TestCase):
    def assert_contract(self, result, evidence="p158-advanced-capture"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P158-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_cause_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["motionAlignmentPresent"], True)
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "assuming-slow-path-is-vendor-blocking")
        self.assertIn(_GATE.MOTION_RULE, " ".join(result["reasons"]))

    def test_slow_path_as_vendor_blocking_is_rejected(self):
        result = evaluate(payload(
            bottleneckCause="scheduling",
            attributedTo="vendor-blocking",
            isolated=False,
            proposedModification=True,
            stagesMeasured=["acquisition-only"],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MODIFICATION_WITHOUT_ISOLATION, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_firmware_attribution_without_isolation_is_rejected(self):
        result = evaluate(payload(
            bottleneckCause="storage",
            attributedTo="firmware-restriction",
            isolated=False,
            proposedModification=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.MODIFICATION_WITHOUT_ISOLATION, result["rejectedClaims"])

    def test_advertising_stops_without_motion_alignment_is_rejected(self):
        result = evaluate(payload(claimsExtraStops=2, motionAlignment=None))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.MERGED_DR_WITHOUT_MOTION, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p158-tc01-saved-source"
        result = evaluate(payload(evidenceId=evidence, repeat="saved-source"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(bottleneckCause="thermal"))
        with self.assertRaises(ValueError):
            evaluate(payload(stagesMeasured=[]))
