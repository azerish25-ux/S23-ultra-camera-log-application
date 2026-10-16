"""Tests for TC-P124-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p124_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p124_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    frames = list(range(10))
    base = {
        "evidenceId": "p124-evidence",
        "repeat": "Repeat",
        "chunks": [{"start": 0, "end": 5}, {"start": 5, "end": 9}],
        "assembledFrames": frames,
        "intendedFrames": frames,
        "boundaryFrameIndex": 5,
        "resumeFrame": 6,
        "callsResume": True,
    }
    base.update(overrides)
    return base


class TCP12407(unittest.TestCase):
    def assert_contract(self, result, evidence="p124-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P124-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("resumeIndex=6", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_deduped_overlap_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("overlap was recomputed and each overlap frame was emitted once", result["reasons"])

    def test_duplicated_overlap_fails_cadence_integrity(self):
        frames = list(range(10)) + [5]
        result = evaluate(payload(assembledFrames=frames))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicated-overlap-frame", result["rejectedClaims"])
        self.assertIn("cadence-integrity", result["rejectedClaims"])
        self.assertIn("p124-evidence", result["preservedResults"])

    def test_omitted_boundary_frame_is_rejected(self):
        frames = [frame for frame in range(10) if frame != 5]
        result = evaluate(payload(assembledFrames=frames))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("omitted-output-frame", result["rejectedClaims"])
        self.assertIn("cadence-integrity", result["rejectedClaims"])

    def test_resume_at_zero_is_rejected(self):
        result = evaluate(payload(resumeFrame=0))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("resume-restarted-at-zero", result["rejectedClaims"])
        self.assertIn("resume-not-at-frame-index-plus-one", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p124-fractional"
        result = evaluate(payload(evidenceId=evidence, repeat="fractional"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
