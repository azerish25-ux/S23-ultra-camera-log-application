"""Tests for TC-P123-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p123_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p123_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def record(**overrides):
    base = {
        "sourceId": "source-a",
        "modelId": "model-a",
        "profileId": "profile-a",
        "graphId": "graph-a",
        "filename": "chunk.bin",
        "frameNumber": 12,
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "evidenceId": "p123-checkpoint",
        "checkpoint": record(),
        "current": record(),
        "action": "resume",
        "repeat": "source",
    }
    base.update(overrides)
    return base


class TCP12303(unittest.TestCase):
    def assert_contract(self, result, evidence="p123-checkpoint"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P123-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Checkpoint identity mismatch")
        self.assertEqual(_MODULE.NEGATIVE, "Filename and frame number alone must not validate a checkpoint.")
        self.assertIn("one changed identity field", _MODULE.REPEAT)

    def test_matching_identity_resumes_even_if_the_filename_differs(self):
        result = evaluate(payload(current=record(filename="other.bin", frameNumber=40)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["changed"], [])
        self.assertFalse(result["preservedResults"][2]["filenameAndFrameMatch"])

    def test_filename_and_frame_alone_do_not_validate_resume(self):
        result = evaluate(payload(current=record(modelId="model-b"), repeat="model"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("checkpoint-identity-mismatch", result["rejectedClaims"])
        self.assertIn("filename-and-frame-number-alone", result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertEqual(result["preservedResults"][2]["changed"], ["modelId"])
        self.assertEqual(result["preservedResults"][1]["checkpoint"]["modelId"], "model-a")

    def test_distinct_job_with_one_new_identity_is_recorded(self):
        result = evaluate(
            payload(action="distinct-job", current=record(graphId="graph-b"), repeat="graph", evidenceId="p123-distinct")
        )
        self.assert_contract(result, "p123-distinct")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["action"], "distinct-job")
        self.assertEqual(result["preservedResults"][2]["changed"], ["graphId"])

    def test_distinct_job_without_a_new_identity_is_rejected(self):
        result = evaluate(payload(action="distinct-job"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("distinct-job-without-new-identity", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(current=record(sourceId="source-b", profileId="profile-b"), repeat="source"))
        with self.assertRaises(ValueError):
            evaluate(payload(action="reuse"))
