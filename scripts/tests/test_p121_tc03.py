"""Tests for TC-P121-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p121_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p121_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p121-checkpoint",
        "repeat": "source",
        "checkpointSource": "src-a",
        "checkpointModel": "model-a",
        "checkpointProfile": "profile-a",
        "checkpointGraph": "graph-a",
        "checkpointFilename": "clip.mov",
        "checkpointFrame": 12,
        "currentSource": "src-a",
        "currentModel": "model-a",
        "currentProfile": "profile-a",
        "currentGraph": "graph-a",
        "currentFilename": "clip.mov",
        "currentFrame": 12,
        "resumeRequested": True,
    }
    base.update(overrides)
    return base


class TCP12103(unittest.TestCase):
    def assert_contract(self, result, evidence="p121-checkpoint"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P121-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Checkpoint identity mismatch")
        self.assertEqual(
            _MODULE.INTERVENTION,
            "Replace source, model, profile, or graph while retaining a previously completed chunk cache.",
        )
        self.assertEqual(
            _MODULE.EXPECTED,
            "Reject incompatible resume data or start a distinct job with new identities.",
        )
        self.assertEqual(_MODULE.NEGATIVE, "Filename and frame number alone must not validate a checkpoint.")
        self.assertEqual(
            _MODULE.REPEAT,
            "Repeat one changed identity field at a time and inspect specific rejection reasons.",
        )

    def test_matching_identity_can_resume(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][1]["distinctJob"])

    def test_filename_and_frame_do_not_validate_a_changed_source(self):
        result = evaluate(payload(currentSource="src-b"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("checkpoint-source-mismatch", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["checkpoint"]["source"], "src-a")
        self.assertEqual(kept["current"]["source"], "src-b")
        self.assertEqual(kept["frame"], 12)

    def test_one_changed_field_starts_a_distinct_job_when_not_resumed(self):
        model = evaluate(payload(repeat="model", currentModel="model-b", resumeRequested=False))
        self.assertEqual(model["decision"], "recorded")
        self.assertEqual(model["rejectedClaims"], [])
        self.assertTrue(model["preservedResults"][1]["distinctJob"])
        self.assertIn("model", model["preservedResults"][1]["changed"])
        profile = evaluate(payload(repeat="profile", currentProfile="profile-b"))
        self.assertEqual(profile["decision"], "rejected")
        self.assertIn("checkpoint-profile-mismatch", profile["rejectedClaims"])
        graph = evaluate(
            payload(repeat="graph", currentGraph="graph-b", currentFilename="other.mov", currentFrame=3)
        )
        self.assertEqual(graph["decision"], "rejected")
        self.assertIn("checkpoint-graph-mismatch", graph["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, graph["rejectedClaims"])

    def test_filename_change_alone_does_not_break_identity(self):
        result = evaluate(payload(currentFilename="renamed.mov"))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["changed"], [])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(checkpointFrame=-1))
        with self.assertRaises(ValueError):
            evaluate(payload(repeat="filename"))
