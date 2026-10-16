"""Tests for TC-P128-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p128_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p128_tc03.py",
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
        "checkpointFilename": "chunk-0002.cache",
        "checkpointFrame": 2,
        "cachedSource": "source-a",
        "cachedModel": "model-a",
        "cachedProfile": "profile-a",
        "cachedGraph": "graph-a",
        "resumeSource": "source-a",
        "resumeModel": "model-a",
        "resumeProfile": "profile-a",
        "resumeGraph": "graph-a",
        "acceptedResume": True,
    }
    base.update(_long_form())
    base.update(overrides)
    return base


def blob(result):
    return " ".join(result["reasons"] + result["preservedResults"])


class TCP12803(unittest.TestCase):
    def assert_contract(self, result, evidence="p128-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P128-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frameAccount=", blob(result))
        self.assertIn("filename and frame number are not checkpoint validation", result["reasons"])
        self.assertTrue(result["reasons"])

    def test_matching_identity_may_resume(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("checkpoint identity matches source, model, profile, and graph", result["reasons"])
        self.assertIn("frameAccount=6/6", blob(result))

    def test_each_changed_identity_field_rejects_an_accepted_resume(self):
        for field, value in (
            ("resumeSource", "source-b"),
            ("resumeModel", "model-b"),
            ("resumeProfile", "profile-b"),
            ("resumeGraph", "graph-b"),
        ):
            with self.subTest(field=field):
                result = evaluate(payload(**{field: value}))
                self.assert_contract(result)
                self.assertEqual(result["decision"], "rejected")
                self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
                self.assertIn(field.removeprefix("resume").lower(), blob(result))

    def test_mismatched_identity_is_recorded_when_resume_is_refused(self):
        result = evaluate(payload(resumeModel="model-b", acceptedResume=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("incompatible resume rejected for model", result["reasons"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_duplicate_frame_is_rejected_inside_the_case(self):
        result = evaluate(payload(accounted_frames=[0, 1, 2, 3, 4, 4]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("duplicate-frame-index", result["rejectedClaims"])
        self.assertIn("missing-frame-index", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p128-graph"
        result = evaluate(payload(evidenceId=evidence, repeat="graph"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
