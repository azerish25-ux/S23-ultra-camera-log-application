"""Tests for TC-P108-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p108_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p108_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_GATE_SPEC = importlib.util.spec_from_file_location(
    "p108_detect_occlusion_and_scene_discontinuities_for_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p108_detect_occlusion_and_scene_discontinuities.py",
)
_GATE = importlib.util.module_from_spec(_GATE_SPEC)
_GATE_SPEC.loader.exec_module(_GATE)

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
COUNT_KEYS = ("discontinuity_count", "occlusion_count", "unknown_count")


def payload(**overrides):
    base = {'depthSamples': [1.0, 1.05, 1.08],
 'threshold': 0.5,
 'flows': [{'dx': 0.2, 'dy': 0.0, 'rdx': -0.2, 'rdy': 0.0}],
 'flow_threshold': 0.25,
 'smoothed': False,
 'sampleLabels': ['measured', 'measured', 'measured'],
 'outputLabels': ['measured', 'measured', 'measured'],
 'evidenceId': 'p108-tc05',
 'repeat': 'backlighting',
 'coverage': [0.0, 0.35, 1.0],
 'halo': 0.02,
 'haloLimit': 0.05,
 'claimsBoundaryQuality': True}
    base.update(overrides)
    return base


class TCP10805(unittest.TestCase):
    def assert_contract(self, result, evidence):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P108-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn(_GATE.OPEN_QUESTION, result["openQuestions"])
        self.assertIn(_MODULE.EXPECTED, result["reasons"])
        self.assertTrue(result["reasons"])
        counts = result["preservedResults"][2]
        self.assertEqual(tuple(counts), COUNT_KEYS)
        for key in COUNT_KEYS:
            self.assertIn(f"{key}={counts[key]}", result["reasons"])

    def test_good_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result, "p108-tc05")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(**{'coverage': [0.0, 0.0, 1.0, 1.0], 'claimsBoundaryQuality': True}))
        self.assert_contract(result, "p108-tc05")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn('dilated-binary-person-mask', result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p108-tc05", result["preservedResults"])

    def test_second_evidence_id_is_preserved(self):
        evidence = 'p108-tc05-contrast'
        result = evaluate(payload(evidenceId=evidence, repeat='foreground-background-contrast'))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(depthSamples=[0.1, float("nan")]))
        with self.assertRaises(ValueError):
            evaluate(payload(evidenceId=" padded"))
