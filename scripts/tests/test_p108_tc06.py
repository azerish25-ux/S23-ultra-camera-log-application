"""Tests for TC-P108-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p108_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p108_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

_GATE_SPEC = importlib.util.spec_from_file_location(
    "p108_detect_occlusion_and_scene_discontinuities_for_tc06",
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
 'evidenceId': 'p108-tc06',
 'repeat': 'brief-occlusion',
 'selectedTarget': 'face-a',
 'nearestFaceByFrame': ['face-a', 'face-b', 'face-b'],
 'chosenFaceByFrame': ['face-a', 'face-a', 'face-a']}
    base.update(overrides)
    return base


class TCP10806(unittest.TestCase):
    def assert_contract(self, result, evidence):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P108-06")
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
        self.assert_contract(result, "p108-tc06")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(**{'nearestFaceByFrame': ['face-a', 'face-b', 'face-b'],
 'chosenFaceByFrame': ['face-a', 'face-b', 'face-b']}))
        self.assert_contract(result, "p108-tc06")
        self.assertEqual(result["decision"], "rejected")
        self.assertIn('nearest-face-independently-every-frame', result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("p108-tc06", result["preservedResults"])

    def test_second_evidence_id_is_preserved(self):
        evidence = 'p108-tc06-reentry'
        result = evaluate(payload(evidenceId=evidence, repeat='re-entry'))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(depthSamples=[0.1, float("nan")]))
        with self.assertRaises(ValueError):
            evaluate(payload(evidenceId=" padded"))
