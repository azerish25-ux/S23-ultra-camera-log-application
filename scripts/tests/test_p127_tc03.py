"""Tests for TC-P127-03."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc03",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc03.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
OTHER = "d" * 64
RECIPE = "b" * 64
RESULT = "c" * 64


def manifest(**overrides):
    value = {
        "source_sha256": SRC,
        "recipe_version_sha256": RECIPE,
        "result_sha256": RESULT,
        "color_transfer": "bt709",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def ident(**overrides):
    value = {
        "sourceSha256": SRC,
        "modelId": "model-a",
        "profileId": "profile-a",
        "graphId": "graph-a",
        "filename": "chunk.mov",
        "frameNumber": 12,
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "source",
        "filename": "chunk.mov",
        "labels": ["Rec.709"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": None,
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "checkpoint": ident(),
        "current": ident(),
        "resumeAccepted": True,
        "distinctJob": False,
    }
    base.update(overrides)
    return base


class TCP12703(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-03")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("checkpointSource=" + SRC, result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_matching_identity_is_recorded(self):
        result = evaluate(payload(current=ident(filename="renamed.mov", frameNumber=40)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("filename and frame number were not the identity", " ".join(result["reasons"]))

    def test_filename_and_frame_alone_do_not_validate_resume(self):
        result = evaluate(payload(current=ident(sourceSha256=OTHER)))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.MISMATCH_TOKEN, result["rejectedClaims"])
        self.assertIn("identity changed: sourceSha256", result["reasons"])

    def test_each_identity_field_rejects_resume(self):
        replacements = {
            "sourceSha256": OTHER,
            "modelId": "model-b",
            "profileId": "profile-b",
            "graphId": "graph-b",
        }
        for field, value in replacements.items():
            current = ident(filename="other.mov", frameNumber=3, **{field: value})
            result = evaluate(payload(current=current, repeat=field))
            self.assertEqual(result["decision"], "rejected", field)
            self.assertIn(_MODULE.MISMATCH_TOKEN, result["rejectedClaims"])
            self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
            self.assertIn(field, " ".join(result["reasons"]))

    def test_changed_identity_can_start_a_distinct_job(self):
        result = evaluate(payload(
            current=ident(modelId="model-b"),
            resumeAccepted=False,
            distinctJob=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("distinct job started with new identities", result["reasons"])

    def test_changed_identity_without_a_split_is_rejected(self):
        result = evaluate(payload(
            current=ident(profileId="profile-b", filename="other.mov"),
            resumeAccepted=False,
            distinctJob=False,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STUCK_TOKEN, result["rejectedClaims"])

    def test_false_split_is_rejected(self):
        result = evaluate(payload(distinctJob=True, resumeAccepted=False))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.FALSE_SPLIT_TOKEN, result["rejectedClaims"])

    def test_missing_source_hash_blocks_export(self):
        body = manifest()
        body["source_sha256"] = None
        result = evaluate(payload(manifest=body))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("missing-source-sha256", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(checkpoint=ident(frameNumber=-1)))
