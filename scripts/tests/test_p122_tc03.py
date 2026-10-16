"""Tests for TC-P122-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SOURCE = "a" * 64


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc03",
        "repeat": "Repeat one changed identity field at a time and inspect specific rejection reasons.",
        "filename": "chunk.bin",
        "frameNumber": 12,
        "sourceSha256": SOURCE,
        "modelId": "depth-v1",
        "profileId": "logc3",
        "graphId": "graph-a",
        "cachedFilename": "chunk.bin",
        "cachedFrameNumber": 12,
        "cachedSourceSha256": SOURCE,
        "cachedModelId": "depth-v1",
        "cachedProfileId": "logc3",
        "cachedGraphId": "graph-a",
        "resumeAccepted": True,
        "newJobStarted": False,
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12203(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc03"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_matching_identity_is_recorded_not_qualified(self):
        result = evaluate(payload(filename="renamed.bin"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        digest = _MODULE.identity_sha256(SOURCE, "depth-v1", "logc3", "graph-a")
        self.assertIn(digest, result["preservedResults"])

    def test_filename_and_frame_alone_are_rejected(self):
        result = evaluate(payload(modelId="depth-v2"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.RESUME_TOKEN, result["rejectedClaims"])

    def test_changed_identity_can_start_a_distinct_job(self):
        result = evaluate(payload(profileId="rec709", resumeAccepted=False, newJobStarted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_changed_identity_without_a_new_job_is_rejected(self):
        result = evaluate(payload(graphId="graph-b", resumeAccepted=False, newJobStarted=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.UNRESOLVED_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[0]["version_sha256"] = "d" * 64
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc03-model"
        result = evaluate(payload(evidenceId=evidence, repeat="model field"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(frameNumber=True))
