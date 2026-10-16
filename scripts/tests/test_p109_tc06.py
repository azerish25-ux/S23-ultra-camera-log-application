"""Tests for TC-P109-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p109_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p109_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def frame(nearest, chosen, policy):
    return {"nearestFace": nearest, "chosenFocus": chosen, "policy": policy}


def payload(**overrides):
    base = {
        "evidenceId": "p109-evidence",
        "repeat": "brief occlusion",
        "selectedIdentity": "subject-a",
        "frames": [
            frame("subject-b", "subject-a", "follow-selected"),
            frame("subject-b", "hold", "target-loss"),
        ],
    }
    base.update(overrides)
    return base


class TCP10906(unittest.TestCase):
    def assert_contract(self, result, evidence="p109-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P109-06")
        self.assertIn(result["decision"], {"recorded", "rejected"})
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_selected_identity_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_nearest_face_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(frames=[frame("subject-b", "subject-b", "nearest-face")]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("nearest-face-independently-every-frame", result["rejectedClaims"])

    def test_mutant_focus_jump_is_rejected(self):
        result = evaluate(payload(
            repeat="re-entry",
            frames=[frame("subject-b", "subject-b", "follow-selected")],
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unexplained-focus-jump", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p109-leaving-frame"
        result = evaluate(payload(evidenceId=evidence, repeat="leaving frame"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
