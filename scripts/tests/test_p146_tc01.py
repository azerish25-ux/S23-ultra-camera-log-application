"""Tests for TC-P146-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p146_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p146_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="emulator-only")
    base.update({
        "results": [
            {"id": "host-arithmetic", "status": "pass", "critical": False},
            {"id": "gpu-color", "status": "fail", "critical": True},
            {"id": "physical-codec", "status": "unavailable", "critical": True},
        ],
        "summary": {"pass": 1, "fail": 1, "skip": 0, "unavailable": 1},
        "assertedClaims": [],
        "claimRequirements": {"release-fully-qualified": ["gpu-color", "physical-codec"]},
    })
    base.update(overrides)
    return base


class TCP14601(unittest.TestCase):
    def assert_contract(self, result, evidence="p146-property-mutation"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P146-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_visible_categories_without_blocked_claims_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][1]["nearestNeighborKilled"], True)
        self.assertEqual(_MODULE.CASE["name"], "Skipped test laundering")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "skips-counted-as-passes")

    def test_counting_skips_as_passes_is_rejected(self):
        result = evaluate(payload(summary={"pass": 2, "fail": 1, "skip": 0, "unavailable": 0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_asserting_a_claim_on_failing_evidence_is_rejected(self):
        result = evaluate(payload(assertedClaims=["release-fully-qualified"]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CLAIM_BLOCKED, result["rejectedClaims"])

    def test_hidden_category_is_rejected(self):
        result = evaluate(payload(summary={"pass": 1, "fail": 1, "skip": 0}))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.CATEGORY_HIDDEN, result["rejectedClaims"])

    def test_identical_metadata_is_rejected_inside_the_case(self):
        result = evaluate(payload(propertySuite=_GATE.identical_property_suite()))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.IDENTICAL_METADATA, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p146-tc01-gpu"
        result = evaluate(payload(evidenceId=evidence, repeat="GPU-unavailable"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(results=[]))
