"""Tests for TC-P101-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc08",
        "repeat": "warm operation",
        "modelLatencyMs": 12.5,
        "captureMs": 16.0,
        "renderMs": 4.0,
        "encodeMs": 6.0,
        "frameBudgetMs": 33.333,
        "operation": "deferred",
        "reportedAsFrameRateGuarantee": False,
        "workloadMeasured": True,
    }
    base.update(overrides)
    return base


class TCP10108(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc08"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_deferred_operation_follows_measured_workload(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = " ".join(result["reasons"])
        self.assertIn("workloadMs=38.500000", text)
        self.assertIn("chosenOperation=deferred", text)
        self.assertIn("modelLatencyMs=12.500000 is not a frame-rate guarantee", text)
        self.assertNotIn("fps", text.lower())

    def test_live_operation_is_recorded_inside_budget(self):
        result = evaluate(payload(
            modelLatencyMs=4.0,
            captureMs=8.0,
            renderMs=4.0,
            encodeMs=4.0,
            operation="live",
            repeat="cold start",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("chosenOperation=live", " ".join(result["reasons"]))
        self.assertIn("workloadMs=20.000000", " ".join(result["reasons"]))

    def test_latency_as_frame_rate_guarantee_is_rejected(self):
        result = evaluate(payload(reportedAsFrameRateGuarantee=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("standalone-model-latency-become-full-camera", result["rejectedClaims"])

    def test_live_choice_from_model_latency_alone_is_rejected(self):
        result = evaluate(payload(operation="live", reportedAsFrameRateGuarantee=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("operation-not-chosen-from-workload-evidence", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc08-thermal"
        result = evaluate(payload(evidenceId=evidence, repeat="severe thermal conditions"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frameBudgetMs=0))
