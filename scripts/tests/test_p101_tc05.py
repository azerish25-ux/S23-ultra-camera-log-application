"""Tests for TC-P101-05."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p101_tc05",
    Path(__file__).resolve().parents[1] / "gates" / "p101_tc05.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p101-tc05",
        "repeat": "GPU",
        "initFailed": True,
        "fallbackName": "",
        "fallbackQualified": False,
        "depthDisabled": True,
        "disableReason": "gpu-delegate-unavailable",
        "silentBackendChange": False,
        "uploadsFrames": False,
    }
    base.update(overrides)
    return base


class TCP10105(unittest.TestCase):
    def assert_contract(self, result, evidence="p101-tc05"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P101-05")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any("physical S23 measurement was not run" in item for item in result["openQuestions"]))

    def test_disabled_depth_with_a_reason_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("depth-disabled=gpu-delegate-unavailable", " ".join(result["reasons"]))

    def test_explicit_cpu_reference_fallback_is_recorded(self):
        result = evaluate(payload(
            fallbackName="cpu-reference",
            fallbackQualified=True,
            depthDisabled=False,
            disableReason="",
            repeat="CPU",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertIn("qualified-fallback=cpu-reference", " ".join(result["reasons"]))

    def test_untested_backend_or_upload_is_rejected(self):
        silent = evaluate(payload(silentBackendChange=True))
        upload = evaluate(payload(uploadsFrames=True, fallbackName="cpu-reference", fallbackQualified=True))
        self.assert_contract(silent)
        self.assert_contract(upload)
        self.assertEqual(silent["decision"], "rejected")
        self.assertEqual(upload["decision"], "rejected")
        self.assertIn("silently-changing-untested-backend-uploading-frames", silent["rejectedClaims"])
        self.assertIn("silently-changing-untested-backend-uploading-frames", upload["rejectedClaims"])

    def test_caller_flag_does_not_qualify_an_unknown_fallback(self):
        result = evaluate(payload(
            fallbackName="mystery-npu",
            fallbackQualified=True,
            depthDisabled=False,
            disableReason="",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("delegate-failure-without-qualified-fallback", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p101-tc05-cpu"
        result = evaluate(payload(evidenceId=evidence, repeat="CPU"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(initFailed=1))
