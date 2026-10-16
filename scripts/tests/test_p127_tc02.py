"""Tests for TC-P127-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
RECIPE = "b" * 64
RESULT = "c" * 64
NEW = "d" * 64


def manifest(**overrides):
    value = {
        "source_sha256": SRC,
        "recipe_version_sha256": RECIPE,
        "result_sha256": RESULT,
        "color_transfer": "logc3",
        "container": "mov",
        "non_claims": ["not a physical S23 qualification"],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "stock",
        "filename": "grade.mov",
        "labels": ["LogC3"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": {"transfer": "logc3", "note": "scene-referred LogC3"},
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "frozenRecipeSha256": RECIPE,
        "frozenParameters": {"stock": "neutral", "focus": "2.4m"},
        "liveParameters": {"stock": "neutral", "focus": "2.4m"},
        "framesUsedLiveSliders": False,
        "newVersionCreated": False,
        "newVersionRecipeSha256": None,
    }
    base.update(overrides)
    return base


class TCP12702(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("frozenRecipeSha256=" + RECIPE, result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_frozen_recipe_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("running job bound to frozen recipe " + RECIPE, result["reasons"])
        self.assertIn("output frames stayed on the frozen parameters", result["reasons"])

    def test_live_sliders_are_rejected(self):
        result = evaluate(payload(
            framesUsedLiveSliders=True,
            liveParameters={"stock": "warm", "focus": "2.4m"},
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.VERSION_TOKEN, result["rejectedClaims"])

    def test_edit_without_a_new_version_is_rejected(self):
        result = evaluate(payload(liveParameters={"stock": "neutral", "focus": "4m", "grain": "7"}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.VERSION_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_new_version_keeps_the_running_job_frozen(self):
        result = evaluate(payload(
            liveParameters={"stock": "warm", "focus": "1m"},
            newVersionCreated=True,
            newVersionRecipeSha256=NEW,
            repeat="focus",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("new recipe version " + NEW, result["reasons"])
        self.assertIn("running job bound to frozen recipe " + RECIPE, result["reasons"])

    def test_reused_frozen_hash_is_rejected(self):
        result = evaluate(payload(
            liveParameters={"stock": "warm", "focus": "1m"},
            newVersionCreated=True,
            newVersionRecipeSha256=RECIPE,
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REUSED_TOKEN, result["rejectedClaims"])

    def test_job_that_leaves_the_frozen_recipe_is_rejected(self):
        result = evaluate(payload(frozenRecipeSha256="e" * 64))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.BINDING_TOKEN, result["rejectedClaims"])

    def test_graded_hash_collision_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(
            manifest=manifest(result_sha256=SRC, color_transfer="bt709"),
            labels=["Rec.709"],
            interpretation=None,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("graded-result-reuses-source-hash", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(newVersionRecipeSha256=NEW))
