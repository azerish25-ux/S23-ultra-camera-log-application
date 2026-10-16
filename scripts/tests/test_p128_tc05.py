"""Tests for TC-P128-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def _long_form(**overrides):
    value = {
        "expected_frames": 6,
        "accounted_frames": [0, 1, 2, 3, 4, 5],
        "checkpoint_frames": [0, 2, 5],
        "audio_duration": 0.25,
        "video_duration": 0.25,
        "audio_absent": False,
        "spot_check_only": False,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p128-evidence",
        "repeat": "Repeat",
        "remainingBytes": 1000,
        "intermediateBytes": 400,
        "duplicatePublicationBytes": 300,
        "finalOutputBytes": 200,
        "proceeded": True,
        "sourcePreserved": True,
        "recoverableArtifacts": True,
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12805(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("requiredBytes=900", blob(result))
        self.assertIn("frameAccount=", blob(result))
        self.assertTrue(result["reasons"])

    def test_full_budget_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("budget covers intermediate, duplicate publication, and final output", result["reasons"])

    def test_safe_pause_is_recorded(self):
        result = evaluate(payload(remainingBytes=100, proceeded=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("paused or failed safely before source loss", result["reasons"])

    def test_budgeting_only_final_output_bytes_is_rejected(self):
        result = evaluate(payload(remainingBytes=250, proceeded=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_proceeding_below_the_final_output_budget_is_rejected(self):
        result = evaluate(payload(remainingBytes=50, proceeded=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.PROCEEDED_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 0, 1, 2, 3, 4, 5]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-assembly"
        result = evaluate(payload(evidenceId=evidence, repeat="assembly"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
            evaluate(payload(remainingBytes=-1))
