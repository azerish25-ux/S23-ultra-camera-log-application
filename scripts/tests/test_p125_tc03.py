"""Tests for TC-P125-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p125_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p125_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
IDENTITY = {"source": "raw-a", "model": "m1", "profile": "p1", "graph": "g1"}


def payload(**overrides):
    base = {
        "evidenceId": "p125-checkpoint",
        "repeat": "source",
        "changedField": "none",
        "checkpointFilename": "chunk-0001",
        "checkpointFrame": 10,
        "checkpointIdentity": dict(IDENTITY),
        "currentIdentity": dict(IDENTITY),
        "resumeAccepted": True,
        "distinctJob": False,
    }
    base.update(overrides)
    return base


class TCP12503(unittest.TestCase):
    def assert_contract(self, result, evidence="p125-checkpoint"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P125-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23" in item for item in result["openQuestions"]))

    def test_constants(self):
        self.assertEqual(_MODULE.NAME, "Checkpoint identity mismatch")
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
        self.assertEqual(result["preservedResults"][1]["checkpointFrame"], 10)

    def test_filename_and_frame_alone_do_not_resume(self):
        current = dict(IDENTITY)
        current["model"] = "m2"
        result = evaluate(
            payload(repeat="model", changedField="model", currentIdentity=current, resumeAccepted=True)
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FILENAME_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        kept = result["preservedResults"][1]
        self.assertEqual(kept["checkpointFilename"], "chunk-0001")
        self.assertEqual(kept["changedFields"], ["model"])
        self.assertEqual(kept["checkpointIdentity"]["model"], "m1")

    def test_distinct_job_is_recorded_when_resume_is_refused(self):
        current = dict(IDENTITY)
        current["graph"] = "g2"
        result = evaluate(
            payload(
                evidenceId="p125-distinct",
                repeat="graph",
                changedField="graph",
                currentIdentity=current,
                resumeAccepted=False,
                distinctJob=True,
            )
        )
        self.assert_contract(result, "p125-distinct")
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][1]["currentIdentity"]["graph"], "g2")

    def test_two_changed_fields_raise(self):
        current = dict(IDENTITY)
        current["source"] = "raw-b"
        current["profile"] = "p2"
        with self.assertRaises(ValueError):
            evaluate(payload(changedField="source", currentIdentity=current))
        with self.assertRaises(ValueError):
            evaluate({})
