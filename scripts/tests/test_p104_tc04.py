"""Tests for TC-P104-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc04",
        "session": "first-install",
        "networkingEnabled": False,
        "assetState": "missing",
        "hangForCloud": False,
        "capturePreserved": True,
        "sourceRetained": True,
        "missingCapabilityReported": True,
    }
    base.update(overrides)
    return base


class TCP10404(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_offline_miss_keeps_capture(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertIn("capture-preserved:true", result["preservedResults"])
        self.assertIn("source-retained:true", result["preservedResults"])
        self.assertIn("asset-state:missing", result["preservedResults"])

    def test_negative_cloud_hang_is_rejected(self):
        result = evaluate(payload(hangForCloud=True, assetState="corrupt"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, result["reasons"])
        self.assertIn("hang-for-cloud:true", result["preservedResults"])
        self.assertIn("capture-preserved:true", result["preservedResults"])
        dropped = evaluate(payload(capturePreserved=False, sourceRetained=False))
        self.assertIn("capture-or-source-not-retained", dropped["rejectedClaims"])
        self.assertIn("capture-preserved:false", dropped["preservedResults"])

    def test_evidence_change(self):
        evidence = "p104-tc04-update"
        result = evaluate(payload(evidenceId=evidence, session="asset-update", assetState="corrupt"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        prior = evaluate(payload(session="previously-working", assetState="present", missingCapabilityReported=False))
        self.assertEqual(prior["decision"], "recorded")
        self.assertIn("session:previously-working", prior["preservedResults"])

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(session="cloud"),
            payload(assetState="gone"),
            payload(networkingEnabled="off"),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
