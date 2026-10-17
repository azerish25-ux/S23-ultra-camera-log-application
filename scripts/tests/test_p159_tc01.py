"""Tests for TC-P159-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p159_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p159_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def stages():
    return [
        {"id": "acquisition-only", "cause": "storage"},
        {"id": "saved-source", "cause": "scheduling"},
        {"id": "development", "cause": "development"},
        {"id": "encoder-stage", "cause": "encoder"},
    ]


def payload(**overrides):
    base = _GATE.core_payload(repeat="acquisition-only")
    base.update({
        "stages": stages(),
        "isolated": True,
        "proposedModification": "none",
        "slowPathAssumedVendorBlocking": False,
    })
    base.update(overrides)
    return base


class TCP15901(unittest.TestCase):
    def assert_contract(self, result, evidence="p159-computational-optics"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P159-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_isolated_storage_and_scheduling_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(
            result["preservedResults"][3]["causes"],
            ["storage", "scheduling", "development", "encoder"],
        )
        self.assertEqual(_MODULE.CASE["name"], "Wrong bottleneck attribution")
        self.assertFalse(result["preservedResults"][1]["candidates"][0]["adopted"])

    def test_assuming_vendor_blocking_is_rejected(self):
        result = evaluate(payload(
            slowPathAssumedVendorBlocking=True,
            proposedModification="firmware",
            isolated=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.BOTTLENECK_NOT_ISOLATED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_firmware_proposal_for_a_storage_cause_is_rejected_after_isolation(self):
        result = evaluate(payload(proposedModification="firmware"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.BOTTLENECK_NOT_ISOLATED, result["rejectedClaims"])

    def test_isolated_firmware_cause_can_propose_a_firmware_change(self):
        rows = [
            {"id": "acquisition-only", "cause": "firmware"},
            {"id": "encoder-stage", "cause": "encoder"},
        ]
        result = evaluate(payload(stages=rows, proposedModification="firmware"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_rank_only_adoption_is_rejected_inside_the_case(self):
        candidate = _GATE.fixture_candidate(
            adopted=True,
            candidate_error=_GATE.FIXTURE_BASELINE_ERROR,
            citedReasons=["benchmark_rank"],
            memoryBytes=400,
            deferredTimeMs=300,
            licenseDeclared=True,
            converted=True,
            difficultScenesValidated=True,
        )
        result = evaluate(payload(candidates=[candidate]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.RANK_ONLY_ADOPTION, result["rejectedClaims"])
        self.assertIn(_GATE.ONLY_RANK_CITED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p159-tc01-saved-source"
        result = evaluate(payload(evidenceId=evidence, repeat="saved-source"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(stages=[]))
        with self.assertRaises(ValueError):
            evaluate(payload(proposedModification="flash"))
