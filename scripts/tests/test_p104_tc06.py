"""Tests for TC-P104-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


_SPEC = importlib.util.spec_from_file_location(
    "p104_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p104_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p104-tc06",
        "motion": "rapid",
        "sourceTimestamp": 1000,
        "depthTimestamp": 900,
        "sourceCrop": "0,0,1920,1080",
        "depthCrop": "0,0,1280,720",
        "hasTemporalIdentity": True,
        "hasGeometricIdentity": True,
        "policy": "reject",
    }
    base.update(overrides)
    return base


class TCP10406(unittest.TestCase):
    def assert_contract(self, result, evidence="p104-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P104-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertEqual(result["openQuestions"][0], "physical S23 measurement was not run")

    def test_good_reject_or_reproject_keeps_identity(self):
        rejected = evaluate(payload())
        self.assert_contract(rejected)
        self.assertEqual(rejected["decision"], "recorded")
        self.assertEqual(rejected["rejectedClaims"], [])
        self.assertIn("stale:true", rejected["preservedResults"])
        self.assertIn("policy:reject", rejected["preservedResults"])
        reprojected = evaluate(payload(policy="reproject", motion="rotation"))
        self.assertEqual(reprojected["decision"], "recorded")
        self.assertIn("policy:reproject", reprojected["preservedResults"])

    def test_negative_blind_array_without_identity(self):
        blind = evaluate(payload(policy="apply-blind"))
        self.assertEqual(blind["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, blind["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE, blind["reasons"])
        self.assertIn("source-timestamp:1000", blind["preservedResults"])
        self.assertIn("depth-timestamp:900", blind["preservedResults"])
        nameless = evaluate(payload(policy="reproject", hasTemporalIdentity=False, hasGeometricIdentity=False))
        self.assertEqual(nameless["decision"], "rejected")
        self.assertIn("temporal-identity:false", nameless["preservedResults"])
        self.assertIn("geometric-identity:false", nameless["preservedResults"])

    def test_evidence_change(self):
        evidence = "p104-tc06-cut"
        result = evaluate(payload(evidenceId=evidence, motion="scene-cut", policy="reproject"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        switch = evaluate(payload(motion="source-switch", policy="reject"))
        self.assertEqual(switch["decision"], "recorded")

    def test_invalid_payload_raises(self):
        cases = (
            {},
            {**payload(), "applyNegative": True},
            payload(motion="dolly"),
            payload(policy="qualified"),
            payload(sourceTimestamp=-1),
            payload(hasTemporalIdentity="yes"),
            payload(sourceCrop=""),
        )
        for item in cases:
            with self.subTest(payload=item):
                with self.assertRaises(ValueError):
                    evaluate(item)


if __name__ == "__main__":
    unittest.main()
