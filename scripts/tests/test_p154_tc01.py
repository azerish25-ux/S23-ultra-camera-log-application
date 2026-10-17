"""Tests for TC-P154-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p154_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p154_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def measurements():
    return [
        {"stage": "acquisition-only", "cause": "storage", "isolated": True},
        {"stage": "saved-source", "cause": "storage", "isolated": True},
        {"stage": "development", "cause": "scheduling", "isolated": True},
        {"stage": "encoder-stage", "cause": "storage", "isolated": True},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="acquisition-only")
    base.update({
        "measurements": measurements(),
        "attributesEverySlowPathToVendor": False,
        "proposesLowLevelModification": False,
    })
    base.update(overrides)
    return base


class TCP15401(unittest.TestCase):
    def assert_contract(self, result, evidence="p154-firmware-hal-survey"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P154-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_limit_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["measurements"][0]["cause"], "storage")
        self.assertFalse(result["preservedResults"][1]["phone_modified"])
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "every-slow-path-is-vendor-blocking")

    def test_assuming_every_slow_path_is_vendor_blocking_is_rejected(self):
        result = evaluate(payload(attributesEverySlowPathToVendor=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p154-firmware-hal-survey", result["preservedResults"])

    def test_modification_before_isolation_is_rejected(self):
        rows = measurements()
        rows[0]["isolated"] = False
        result = evaluate(payload(measurements=rows, proposesLowLevelModification=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNISOLATED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.THROUGHPUT_NOT_FIRMWARE, result["rejectedClaims"])

    def test_isolated_storage_does_not_justify_firmware_modification(self):
        result = evaluate(payload(proposesLowLevelModification=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.THROUGHPUT_NOT_FIRMWARE, result["rejectedClaims"])
        self.assertNotIn(_MODULE.UNISOLATED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_claims_all_modes_is_still_rejected(self):
        result = evaluate(payload(claims_all_modes=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.CLAIMS_ALL_MODES, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p154-tc01-encoder-stage"
        result = evaluate(payload(evidenceId=evidence, repeat="encoder-stage"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(measurements=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(attributesEverySlowPathToVendor="yes"))
