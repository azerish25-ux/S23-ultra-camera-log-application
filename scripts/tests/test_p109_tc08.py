"""Tests for TC-P109-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "blinded presentation",
        "frameScores": [0.95, 0.2, 0.96],
        "severities": [0, 1, 0],
        "acceptByMean": False,
        "catastrophicRecordedSeparately": True,
        "releaseLimited": True,
    }
    base.update(overrides)
    return base


class TCP10908(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-08")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_separated_failures_are_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("mean-score 0.703333 severe 1", result["reasons"])

    def test_negative_mean_hides_severe_failures_and_evidence_remains(self):
        result = evaluate(payload(acceptByMean=True, frameScores=[0.95, 0.96, 0.97], severities=[0, 1, 0]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("mean-hides-severe-boundary-failures", result["rejectedClaims"])

    def test_mutant_unrecorded_catastrophe_is_rejected(self):
        result = evaluate(payload(
            repeat="aggressive blur",
            acceptByMean=False,
            catastrophicRecordedSeparately=False,
            releaseLimited=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("catastrophic-artifacts-not-recorded-separately", result["rejectedClaims"])
        self.assertIn("release-not-limited-after-severe-failures", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-held-out"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="held-out scenes",
            frameScores=[0.4, 0.6],
            severities=[0, 0],
            acceptByMean=True,
            catastrophicRecordedSeparately=False,
            releaseLimited=False,
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
