"""Tests for TC-P157-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p157_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p157_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def measurements(**overrides):
    rows = [
        {"stage": "acquisition-only", "limitingCause": "storage", "isolated": True},
        {"stage": "saved-source", "limitingCause": "scheduling", "isolated": True},
        {"stage": "development", "limitingCause": "development", "isolated": True},
        {"stage": "encoder-stage", "limitingCause": "encoder", "isolated": True},
    ]
    by_stage = {row["stage"]: row for row in rows}
    for stage, fields in overrides.items():
        by_stage[stage].update(fields)
    return list(by_stage.values())


def payload(**overrides):
    base = _GATE.core_payload()
    base.update({
        "repeat": "acquisition-only",
        "measurements": measurements(),
        "attributedCause": "storage",
        "lowLevelModificationProposed": False,
    })
    base.update(overrides)
    if "experiments" in overrides and "checksum" not in overrides:
        base["checksum"] = _GATE.protocol_checksum(base["experiments"])
    return base


class TCP15701(unittest.TestCase):
    def assert_contract(self, result, evidence="p157-instrumented-experiment-design"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P157-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_limit_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][3]["attributedCause"], "storage")
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "slow-path-assumed-vendor-blocking")

    def test_storage_or_scheduling_called_vendor_blocking_is_rejected(self):
        result = evaluate(payload(attributedCause="firmware-restriction"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_modification_before_isolation_is_rejected(self):
        result = evaluate(payload(
            measurements=measurements(**{"saved-source": {"isolated": False}}),
            lowLevelModificationProposed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.ISOLATION_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["expected"], result["reasons"])

    def test_modification_after_isolation_is_recorded(self):
        result = evaluate(payload(lowLevelModificationProposed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p157-tc01-encoder"
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
            evaluate(payload(attributedCause="magic"))
