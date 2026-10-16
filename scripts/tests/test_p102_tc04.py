"""Tests for TC-P102-04."""

from __future__ import annotations

import hashlib
import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p102_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p102_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p102-evidence",
        "repeat": "first-installation",
        "networkingEnabled": False,
        "waitedForNetwork": False,
        "missingCapabilityReported": True,
        "ordinaryCapturePreserved": True,
        "sourceRetained": True,
        "assetPresent": False,
        "assetContent": None,
        "assetSha256": None,
        "expectedSha256": hashlib.sha256(b"depth-model-asset-v1").hexdigest(),
    }
    base.update(overrides)
    return base


class TCP10204(unittest.TestCase):
    def assert_contract(self, result, evidence="p102-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P102-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertTrue(any(item == "physical S23 measurement was not run" for item in result["openQuestions"]))
        self.assertTrue(result["reasons"])

    def test_good_input_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("asset-missing", result["preservedResults"])

    def test_directive_negative_is_rejected(self):
        result = evaluate(payload(waitedForNetwork=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("offline-camera-hang-waiting-undisclosed-cloud", result["rejectedClaims"])

    def test_changed_evidence_id_is_preserved(self):
        evidence = "p102-tc04-update"
        result = evaluate(payload(evidenceId=evidence, repeat="asset-update"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(assetPresent=True, assetContent="depth-model-asset-v1", assetSha256="0" * 64))
