"""Tests for TC-P103-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p103-evidence",
        "repeat": "Repeat",
        "applyNegative": False,
        "applyMutant": False,
        "filename": "depth-wall-glass.tflite",
        "cachedModelId": "depth-v1-fp16",
        "actualModelId": "depth-v1-fp16",
        "reportedModelId": "depth-v1-fp16",
        "cachedWeightsDigest": "sha256:aaa",
        "actualWeightsDigest": "sha256:aaa",
        "cacheRetained": True,
    }
    base.update(overrides)
    return base


class TCP10301(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(result["reasons"])
        self.assertTrue(any("physical S23 was not run" in item for item in result["openQuestions"]))

    def test_clean_result_is_recorded_not_qualified(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_negative_is_rejected_and_evidence_remains(self):
        result = evaluate(payload(applyNegative=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="with"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])

    def test_filename_match_with_different_weights_is_rejected(self):
        result = evaluate(
            payload(
                cachedModelId="depth-wall-glass.tflite",
                reportedModelId="depth-wall-glass.tflite",
                actualModelId="depth-v2-int8",
                actualWeightsDigest="sha256:bbb",
                cacheRetained=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])

    def test_incompatible_cache_is_invalidated_and_actual_identity_reported(self):
        result = evaluate(
            payload(
                cachedModelId="depth-v1-fp16",
                actualModelId="depth-v2-int8",
                reportedModelId="depth-v2-int8",
                actualWeightsDigest="sha256:bbb",
                cacheRetained=False,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-with"
        result = evaluate(payload(evidenceId=evidence, repeat="with"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
