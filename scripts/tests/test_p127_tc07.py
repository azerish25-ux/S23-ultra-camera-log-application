"""Tests for TC-P127-07."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc07",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc07.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
RECIPE = "b" * 64
RESULT = "c" * 64
INTENDED = [0, 1, 2, 3]


def manifest(**overrides):
    value = {
        "source_sha256": SRC,
        "recipe_version_sha256": RECIPE,
        "result_sha256": RESULT,
        "color_transfer": "hlg",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "fractional",
        "filename": "resume.mov",
        "labels": ["HLG"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": None,
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "intendedFrames": list(INTENDED),
        "emittedFrames": list(INTENDED),
        "playable": True,
        "declaredContinuity": True,
    }
    base.update(overrides)
    return base


class TCP12707(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-07")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("intendedCount=4", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_exact_timeline_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("intended timeline emitted once", result["reasons"])

    def test_playable_duplicated_overlap_fails_cadence(self):
        result = evaluate(payload(emittedFrames=[0, 1, 2, 2, 3], repeat="scene-cut"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CONTINUITY_TOKEN, result["rejectedClaims"])
        self.assertIn("playable movie does not excuse duplicated overlap frames", result["reasons"])
        self.assertIn("duplicatedFrames=2", result["reasons"])

    def test_omitted_boundary_frames_are_rejected(self):
        result = evaluate(payload(emittedFrames=[0, 1, 3], repeat="audio"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OMIT_TOKEN, result["rejectedClaims"])
        self.assertIn("omittedFrames=2", result["reasons"])
        self.assertIn("p127-evidence", result["preservedResults"])

    def test_broken_continuity_flag_is_rejected(self):
        result = evaluate(payload(declaredContinuity=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertEqual(result["rejectedClaims"], [_MODULE.CONTINUITY_TOKEN])

    def test_missing_non_claim_keeps_the_frame_count(self):
        result = evaluate(payload(manifest=manifest(non_claims=["unrelated"])))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-required-non-claim", result["rejectedClaims"])
        self.assertIn("intendedCount=4", result["preservedResults"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(emittedFrames=[]))
