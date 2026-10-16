"""Tests for TC-P111-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p111_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p111_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def track(identity, confidence, focus):
    return {"identity": identity, "confidence": confidence, "focus_distance": focus}


def frame(t_ms, tracks, applied_focus, applied_state, applied_identity):
    return {
        "t_ms": t_ms,
        "tracks": tracks,
        "appliedFocus": applied_focus,
        "appliedState": applied_state,
        "appliedIdentity": applied_identity,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p111-evidence",
        "repeat": "Repeat brief occlusion, leaving frame, re-entry, and low-confidence tracking.",
        "confidenceThreshold": 0.5,
        "maxDistancePerFrame": 0.25,
        "frameMs": 40,
        "selectedIdentity": "subject-a",
        "frames": [
            frame(0, [track("subject-a", 0.9, 2.0), track("subject-b", 0.8, 1.25)], 2.0, "tracking", "subject-a"),
            frame(40, [track("subject-a", 0.2, 2.0), track("subject-b", 0.95, 1.25)], 2.0, "held", "subject-a"),
            frame(80, [track("subject-a", 0.85, 2.25), track("subject-b", 0.9, 1.0)], 2.25, "tracking", "subject-a"),
        ],
    }
    base.update(overrides)
    return base


class TCP11106(unittest.TestCase):
    def assert_contract(self, result, evidence="p111-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P111-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("duration_ms:80", result["preservedResults"])
        self.assertIn("start_distance:2", result["preservedResults"])
        self.assertIn("end_distance:2.25", result["preservedResults"])
        self.assertTrue(any("physical S23" in item and "not run" in item for item in result["openQuestions"]))

    def test_selected_identity_holds_through_the_cross(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(any("held" in item for item in result["reasons"]))

    def test_nearest_face_on_loss_is_rejected(self):
        frames = [
            frame(0, [track("subject-a", 0.9, 2.0), track("subject-b", 0.8, 1.25)], 2.0, "tracking", "subject-a"),
            frame(40, [track("subject-a", 0.2, 2.0), track("subject-b", 0.95, 1.25)], 1.25, "tracking", "subject-b"),
            frame(80, [track("subject-a", 0.85, 2.25), track("subject-b", 0.9, 1.0)], 1.0, "tracking", "subject-b"),
        ]
        result = evaluate(payload(frames=frames))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("jump-on-low-confidence", result["rejectedClaims"])
        self.assertIn("nearest-face-independently-every-frame", result["rejectedClaims"])
        self.assertIn("p111-evidence", result["preservedResults"])

    def test_subject_leaving_frame_holds_the_last_focus(self):
        frames = [
            frame(0, [track("subject-a", 0.9, 2.0), track("subject-b", 0.8, 1.25)], 2.0, "tracking", "subject-a"),
            frame(40, [track("subject-b", 0.95, 1.25)], 2.0, "held", "subject-a"),
        ]
        result = evaluate(payload(frames=frames))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("duration_ms:40", result["preservedResults"])
        self.assertIn("start_distance:2", result["preservedResults"])
        self.assertIn("end_distance:2", result["preservedResults"])

    def test_reacquire_cannot_jump_past_the_pull_limiter(self):
        frames = [
            frame(0, [track("subject-a", 0.9, 2.0), track("subject-b", 0.8, 1.25)], 2.0, "tracking", "subject-a"),
            frame(40, [track("subject-a", 0.2, 2.0), track("subject-b", 0.95, 1.25)], 2.0, "held", "subject-a"),
            frame(80, [track("subject-a", 0.9, 4.0), track("subject-b", 0.8, 1.0)], 4.0, "tracking", "subject-a"),
        ]
        result = evaluate(payload(frames=frames))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("one-frame-jump-exceeds-pull-limiter", result["rejectedClaims"])
        self.assertIn("end_distance:2.25", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=[frame(0, [track("subject-a", 0.1, 2.0)], 2.0, "tracking", "subject-a")]))
