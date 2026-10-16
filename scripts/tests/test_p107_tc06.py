"""Tests for TC-P107-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p107_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p107_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frame(frame_id, **overrides):
    value = {
        "frame_id": frame_id,
        "selected_id": "subject-a",
        "nearest_face_id": "subject-b",
        "target_visible": True,
        "policy": "documented-identity",
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p107-evidence",
        "repeat": "crossing",
        "target_id": "subject-a",
        "frames": [frame("f0"), frame("f1")],
    }
    base.update(overrides)
    return base


class TCP10706(unittest.TestCase):
    def assert_contract(self, result, evidence="p107-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P107-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_documented_identity_is_recorded_when_nearest_face_differs(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("focus_jumps=0", result["preservedResults"])
        self.assertTrue(any("nearest_face_frames=0" in item for item in result["reasons"]))

    def test_nearest_face_each_frame_is_rejected(self):
        result = evaluate(
            payload(
                frames=[
                    frame("f0", policy="nearest-face", selected_id="subject-b", nearest_face_id="subject-b"),
                    frame("f1", policy="nearest-face", selected_id="subject-a", nearest_face_id="subject-a"),
                ]
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-face-per-frame", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])

    def test_target_loss_reset_is_recorded(self):
        evidence = "p107-reentry"
        result = evaluate(
            payload(
                evidenceId=evidence,
                frames=[
                    frame("f0"),
                    frame(
                        "f1",
                        target_visible=False,
                        policy="target-loss-reset",
                        selected_id="none",
                        nearest_face_id="subject-b",
                    ),
                ],
            )
        )
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[]))
        with self.assertRaises(ValueError):
            evaluate({})
