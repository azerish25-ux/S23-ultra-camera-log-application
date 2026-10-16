"""Tests for TC-P102-01."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    material = "variant-b-weights"
    actual = hashlib.sha256(material.encode("utf-8")).hexdigest()
    cached = hashlib.sha256(b"variant-a-weights").hexdigest()
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "precision-change",
        "filename": "depth.tflite",
        "cachedFilename": "depth.tflite",
        "cachedWeightSha256": cached,
        "weightMaterial": material,
        "actualWeightSha256": actual,
        "reportedIdentity": actual,
        "cacheInvalidated": True,
    }
    base.update(overrides)
    return base


class TCP10201(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(reportedIdentity="depth.tflite", cacheInvalidated=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("filename-match-alone-establish-identical-weights", result["rejectedClaims"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc01-repeat"
        result = evaluate(payload(evidenceId=evidence))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        broken = payload(actualWeightSha256="0" * 64)
        with self.assertRaises(ValueError):
            evaluate(broken)
