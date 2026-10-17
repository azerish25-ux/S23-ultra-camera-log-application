"""Tests for TC-P145-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    base = {
        "evidenceId": "p145-tc06",
        "repeat": "pending-render-jobs",
        "signed": True,
        "signingMismatch": False,
        "action": "migrate",
        "sourcesPreserved": True,
        "profilesPreserved": True,
        "recoveryPreserved": True,
        "pendingRenderJobs": 2,
        "migrationInterrupted": False,
        "rollbackWithinLimits": True,
        "scenario": "pending-render-jobs",
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14506(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Update threatens private media")
        self.assertEqual(
            _MODULE.CASE["negative"],
            "Uninstalling silently to solve signing mismatch must fail.",
        )

    def test_signed_migration_keeps_private_media(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][2]["kept"])
        self.assertEqual(result["preservedResults"][2]["pendingRenderJobs"], 2)

    def test_explicit_refusal_on_signing_mismatch_is_recorded(self):
        result = evaluate(payload(
            signingMismatch=True,
            action="refuse",
            scenario="rollback-limits",
            repeat="rollback-limits",
            rollbackWithinLimits=False,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["sourcesPreserved"])

    def test_silent_uninstall_is_rejected_even_if_bytes_remain(self):
        result = evaluate(payload(action="silent-uninstall", signingMismatch=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertTrue(result["preservedResults"][2]["sourcesPreserved"])

    def test_interrupted_migration_that_drops_sources_is_rejected(self):
        result = evaluate(payload(
            migrationInterrupted=True,
            sourcesPreserved=False,
            scenario="interrupted-migration",
            repeat="interrupted-migration",
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NOT_PRESERVED, result["rejectedClaims"])

    def test_unsigned_migration_is_rejected(self):
        result = evaluate(payload(signed=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unsigned-migration", result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc06-interrupted"
        result = evaluate(payload(
            evidenceId=evidence,
            scenario="interrupted-migration",
            repeat="interrupted-migration",
            migrationInterrupted=True,
            action="preserve",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(pendingRenderJobs=-1))
