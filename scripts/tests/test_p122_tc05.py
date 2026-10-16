"""Tests for TC-P122-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p122_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p122_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p122-tc05",
        "repeat": "Repeat before rendering, during chunk assembly, and during gallery publication.",
        "remainingBytes": 1000,
        "intermediateBytes": 100,
        "publicationDuplicateBytes": 100,
        "finalOutputBytes": 50,
        "sourcePreserved": True,
        "action": "proceed",
        "phasePoint": "before-rendering",
        "versions": _MODULE.valid_versions(),
        "mutatedInPlace": False,
    }
    base.update(overrides)
    return base


class TCP12205(unittest.TestCase):
    def assert_contract(self, result, evidence="p122-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P122-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(any(item.startswith("preimage=") for item in result["preservedResults"]))
        self.assertIn("requiredBytes=200", " ".join(result["reasons"] + result["preservedResults"]))
        self.assertTrue(result["reasons"])

    def test_full_budget_is_recorded_not_qualified(self):
        result = evaluate(payload(phasePoint="chunk-assembly"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_final_output_budget_alone_is_rejected(self):
        result = evaluate(payload(
            remainingBytes=100,
            intermediateBytes=80,
            publicationDuplicateBytes=80,
            finalOutputBytes=100,
            phasePoint="gallery-publication",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn("p122-tc05", result["preservedResults"])
        self.assertIn("requiredBytes=160", result["reasons"])

    def test_safe_fail_preserves_the_source(self):
        result = evaluate(payload(remainingBytes=10, action="fail", phasePoint="chunk-assembly"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_source_loss_is_rejected(self):
        result = evaluate(payload(sourcePreserved=False, action="pause"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SOURCE_LOST, result["rejectedClaims"])

    def test_recipe_hash_mismatch_is_rejected(self):
        versions = _MODULE.valid_versions()
        versions[1]["version_sha256"] = "f" * 64
        result = evaluate(payload(versions=versions))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("version-sha256-mismatch", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p122-tc05-gallery"
        result = evaluate(payload(evidenceId=evidence, repeat="gallery publication"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(remainingBytes=-1))
