"""Tests for TC-P103-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc05.py",
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
        "delegateFailed": False,
        "fallbackName": None,
        "fallbackExplicitlyQualified": False,
        "depthDisabled": False,
        "disableReason": "",
        "silentBackendChange": False,
        "uploadedFrames": False,
    }
    base.update(overrides)
    return base


class TCP10305(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-05")
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
        self.assertIn("silently-changing-untested-backend-uploading-frames", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="CPU"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("silently-changing-untested-backend-uploading-frames", result["rejectedClaims"])

    def test_silent_backend_or_upload_is_rejected(self):
        uploaded = evaluate(payload(uploadedFrames=True))
        silent = evaluate(payload(delegateFailed=True, silentBackendChange=True))
        self.assertEqual(uploaded["decision"], "rejected")
        self.assertEqual(silent["decision"], "rejected")
        self.assertIn("silently-changing-untested-backend-uploading-frames", uploaded["rejectedClaims"])
        self.assertIn("p103-evidence", silent["preservedResults"])

    def test_failed_delegate_can_disable_depth_with_a_reason(self):
        result = evaluate(
            payload(
                delegateFailed=True,
                depthDisabled=True,
                disableReason="delegate init failed; optional depth disabled",
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-cpu"
        result = evaluate(payload(evidenceId=evidence, repeat="CPU"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
