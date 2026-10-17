"""Tests for TC-P152-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p152_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p152_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture failure")
    base.update({
        "soleTakeDeleted": False,
        "visualQuality": "excellent",
        "defectFixed": True,
        "regressionExists": True,
        "regressionPasses": True,
        "releaseAllowed": True,
    })
    base.update(overrides)
    return base


class TCP15208(unittest.TestCase):
    def assert_contract(self, result, evidence="p152-production-readiness"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P152-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_retained_take_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertFalse(result["preservedResults"][3]["soleTakeDeleted"])
        self.assertEqual(result["preservedResults"][1]["release_decision"], "go")
        self.assertEqual(_MODULE.CASE["name"], "Critical preservation defect")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "aesthetic-quality-cannot-waive-data-loss")

    def test_excellent_quality_cannot_waive_data_loss(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            visualQuality="excellent",
            defectFixed=False,
            regressionPasses=False,
            releaseAllowed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p152-production-readiness", result["preservedResults"])

    def test_fixed_defect_with_a_passing_regression_is_recorded(self):
        result = evaluate(payload(soleTakeDeleted=True, releaseAllowed=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])

    def test_open_data_loss_without_release_still_blocks(self):
        result = evaluate(payload(
            soleTakeDeleted=True,
            visualQuality="poor",
            defectFixed=False,
            regressionExists=False,
            regressionPasses=False,
            releaseAllowed=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REGRESSION_OPEN, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_dossier_waiver_and_promotional_footage_are_rejected(self):
        risks = _GATE.replace_risk("staging-copy-deleted", status="accepted", reason="")
        evidence = [{"id": "promo-reel", "kind": "promotional-footage"}]
        result = evaluate(payload(
            risks=risks,
            evidence=evidence,
            release_decision="go",
            soleTakeDeleted=True,
            defectFixed=False,
            regressionExists=False,
            regressionPasses=False,
            releaseAllowed=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.DATA_LOSS_WAIVER_REJECTED, result["rejectedClaims"])
        self.assertIn(_GATE.PROMOTIONAL_FOOTAGE, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["regressionEvidenceIds"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p152-tc08-cold-start"
        result = evaluate(payload(evidenceId=evidence, repeat="cold-start recovery"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(soleTakeDeleted="yes"))
            evaluate(payload(release_decision="qualified"))
