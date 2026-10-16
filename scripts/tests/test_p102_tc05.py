"""Tests for TC-P102-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "gpu",
        "delegateInitialized": False,
        "fallback": "disabled",
        "reason": "delegate initialization failed; optional depth disabled",
        "framesUploaded": False,
    }
    base.update(overrides)
    return base


class TCP10205(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-05")
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
        result = evaluate(payload(fallback="untested-backend", framesUploaded=True, reason=""))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silently-changing-untested-backend-uploading-frames", result["rejectedClaims"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc05-cpu"
        result = evaluate(payload(evidenceId=evidence, repeat="cpu"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(fallback="cloud"))
