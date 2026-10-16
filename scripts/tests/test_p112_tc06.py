"""Tests for TC-P112-06."""

from __future__ import annotations

import importlib.util
import statistics
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p112_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p112_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frames(policy="identity"):
    distances = [1.8, 1.8, 2.4, 2.4]
    rows = []
    for index in range(4):
        nearest = "subject-a" if index < 2 else "subject-b"
        visible = index != 2
        if policy == "identity":
            focus = "subject-a" if visible else "hold"
        elif policy == "nearest":
            focus = nearest
        else:
            focus = "subject-c"
        rows.append({
            "selected_id": "subject-a",
            "selected_visible": visible,
            "focus_id": focus,
            "nearest_face_id": nearest,
            "focus_distance": distances[index],
        })
    return rows


def payload(**overrides):
    base = {
        "evidenceId": "p112-tc06",
        "repeat": "crossing",
        "frames": frames("identity"),
    }
    base.update(overrides)
    return base


class TCP11206(unittest.TestCase):
    def assert_contract(self, result, evidence="p112-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P112-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("focus_distance_variance=") for item in result["preservedResults"]))

    def test_selected_identity_and_hold_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        distances = [frame["focus_distance"] for frame in frames("identity")]
        token = "focus_distance_variance=" + repr(float(statistics.variance(distances)))
        self.assertIn(token, result["preservedResults"])

    def test_nearest_face_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(frames=frames("nearest")))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-face-independently-every-frame", result["rejectedClaims"])

    def test_unexplained_jump_is_rejected(self):
        evidence = "p112-tc06-reentry"
        result = evaluate(payload(frames=frames("other"), evidenceId=evidence, repeat="re-entry"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unexplained-focus-jump", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frames=frames("identity")[:1]))
