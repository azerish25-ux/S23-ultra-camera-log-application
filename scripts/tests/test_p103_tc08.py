"""Tests for TC-P103-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p103-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
        "standaloneLatencyMs": 8.0,
        "frameIntervalsMs": [16.6, 16.7, 17.1, 16.9],
        "frameBudgetMs": 33.4,
        "integratedWorkloadMeasured": True,
        "operationChoice": "live",
        "fullCameraFpsClaimedFromStandalone": False,
    }
    base.update(overrides)
    return base


class TCP10308(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("maxFrameIntervalMs=" in item for item in result["reasons"]))

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("standalone-model-latency-become-full-camera", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="cold"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("standalone-model-latency-become-full-camera", result["rejectedClaims"])

    def test_standalone_latency_is_not_a_frame_rate_guarantee(self):
        result = evaluate(payload(fullCameraFpsClaimedFromStandalone=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("standalone-model-latency-become-full-camera", result["rejectedClaims"])

    def test_max_interval_not_the_mean_chooses_deferred(self):
        # Mean is 29 ms, under the 33 ms budget; the 80 ms stall is not averaged away.
        intervals = [10.0, 12.0, 14.0, 80.0]
        deferred = evaluate(payload(frameIntervalsMs=intervals, operationChoice="deferred"))
        live = evaluate(payload(frameIntervalsMs=intervals, operationChoice="live"))
        self.assertEqual(deferred["decision"], "recorded")
        self.assertIn("p103-evidence", deferred["preservedResults"])
        self.assertEqual(live["decision"], "rejected")
        self.assertIn("live-choice-contradicts-integrated-evidence", live["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-cold"
        result = evaluate(payload(evidenceId=evidence, repeat="cold"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
