"""Tests for TC-P103-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p103_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p103_tc06.py",
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
        "hasTemporalIdentity": True,
        "hasGeometricIdentity": True,
        "timestampsMatch": True,
        "cropMatches": True,
        "reprojected": False,
        "reprojectionPolicyValidated": False,
    }
    base.update(overrides)
    return base


class TCP10306(unittest.TestCase):
    def assert_contract(self, result, evidence="p103-evidence"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P103-06")
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
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])

    def test_mutant_is_rejected(self):
        result = evaluate(payload(applyMutant=True, repeat="rapid"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])

    def test_float_array_without_identity_is_rejected(self):
        result = evaluate(payload(hasTemporalIdentity=False, hasGeometricIdentity=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("float-array-without-temporal-geometric-identity", result["rejectedClaims"])

    def test_validated_reprojection_is_recorded(self):
        result = evaluate(
            payload(
                timestampsMatch=False,
                cropMatches=False,
                reprojected=True,
                reprojectionPolicyValidated=True,
            )
        )
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p103-rapid"
        result = evaluate(payload(evidenceId=evidence, repeat="rapid"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
