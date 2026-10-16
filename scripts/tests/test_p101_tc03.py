"""Tests for TC-P101-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc03",
        "repeat": "hair",
        "baseline": [0.10, 0.40, 0.70],
        "exported": [0.11, 0.39, 0.72],
        "tolerance": 0.05,
        "boundaryBaseline": [0.0, 1.0],
        "boundaryExported": [0.01, 0.99],
        "boundaryTolerance": 0.02,
        "loads": True,
        "experimental": False,
    }
    base.update(overrides)
    return base


class TCP10103(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_within_tolerance_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        text = " ".join(result["reasons"])
        self.assertIn("maxAbsError=0.020000", text)
        self.assertIn("boundaryAbsError=0.010000", text)
        self.assertIn("not qualified", text)

    def test_running_outside_tolerance_is_rejected(self):
        result = evaluate(payload(exported=[0.9, 0.1, 0.0], experimental=False, loads=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("model-merely-runs-numerically-qualified", result["rejectedClaims"])

    def test_outside_tolerance_can_remain_experimental(self):
        result = evaluate(payload(exported=[0.9, 0.1, 0.0], experimental=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("remains experimental", " ".join(result["reasons"]))

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc03-glass"
        result = evaluate(payload(evidenceId=evidence, repeat="glass"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(baseline=[0.1, float("nan")]))
