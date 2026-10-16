"""Tests for TC-P127-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p127_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p127_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")
SRC = "a" * 64
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


def payload(**overrides):
    base = {
        "evidenceId": "p127-evidence",
        "repeat": "assembly",
        "filename": "spill.mov",
        "labels": ["Rec.709"],
        "manifest": manifest(),
        "export_allowed": True,
        "grade_applied": True,
        "metadataTexts": [],
        "interpretation": None,
        "selfDescribing": False,
        "publishPrivatePaths": False,
        "personalIdentifiers": [],
        "remainingBytes": 1000,
        "intermediateBytes": 100,
        "duplicatePublicationBytes": 40,
        "finalOutputBytes": 50,
        "budgetScope": "intermediate-and-publication",
        "action": "continue",
        "sourcePreserved": True,
        "recoverableArtifacts": True,
        "cleanupChoices": ["keep-source"],
    }
    base.update(overrides)
    return base


class TCP12705(unittest.TestCase):
    def assert_contract(self, result, evidence="p127-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P127-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertIn("requiredBytes=140", result["preservedResults"])
        self.assertTrue(result["reasons"])

    def test_full_budget_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("requiredBytes=140 finalOutputBytes=50 remainingBytes=1000", result["reasons"])

    def test_final_only_budget_is_rejected(self):
        sneaky = evaluate(payload(
            budgetScope="final-only",
            remainingBytes=60,
            action="continue",
        ))
        self.assert_contract(sneaky)
        self.assertEqual(sneaky["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, sneaky["rejectedClaims"])
        self.assertIn("final-only budget would accept work that does not fit", sneaky["reasons"])
        self.assertIn(_MODULE.CONTINUE_TOKEN, sneaky["rejectedClaims"])
        roomy = evaluate(payload(budgetScope="final-only", remainingBytes=5000))
        self.assertEqual(roomy["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, roomy["rejectedClaims"])

    def test_exhaustion_must_pause_or_fail_and_keep_the_source(self):
        continued = evaluate(payload(remainingBytes=10, action="continue"))
        self.assertEqual(continued["decision"], "rejected")
        self.assertIn(_MODULE.CONTINUE_TOKEN, continued["rejectedClaims"])
        lost = evaluate(payload(remainingBytes=10, action="fail", sourcePreserved=False))
        self.assertIn(_MODULE.SOURCE_TOKEN, lost["rejectedClaims"])
        safe = evaluate(payload(
            remainingBytes=10,
            action="pause",
            cleanupChoices=["delete-intermediates", "keep-source"],
            repeat="publication",
        ))
        self.assert_contract(safe)
        self.assertEqual(safe["decision"], "recorded")
        self.assertIn("paused or failed safely", " ".join(safe["reasons"]))

    def test_missing_cleanup_choice_is_rejected(self):
        result = evaluate(payload(remainingBytes=10, action="fail", cleanupChoices=[]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CLEANUP_TOKEN, result["rejectedClaims"])

    def test_second_evidence_id_is_preserved(self):
        result = evaluate(payload(evidenceId="p127-before-render", repeat="before-render"))
        self.assert_contract(result, "p127-before-render")
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(intermediateBytes=-1))
