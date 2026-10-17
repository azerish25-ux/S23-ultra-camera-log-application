"""Tests for TC-P155-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p155_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p155_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def archive(**overrides):
    value = {
        "favorableOutputs": True,
        "failedExperiments": True,
        "setupDetails": True,
        "promotionalReelOnly": False,
        "domains": ["capture", "film-rendering", "optics", "rejected-hypotheses"],
    }
    value.update(overrides)
    return value


def payload(**overrides):
    base = _GATE.core_payload(repeat="capture")
    base.update({"archive": archive()})
    base.update(overrides)
    return base


class TCP15508(unittest.TestCase):
    def assert_contract(self, result, evidence="p155-reversible-alternatives"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P155-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_failed_experiments_and_setup_are_preserved(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        preserved = result["preservedResults"][3]
        self.assertTrue(preserved["failedExperiments"])
        self.assertTrue(preserved["setupDetails"])
        self.assertFalse(preserved["promotionalReelOnly"])
        self.assertIn("rejected-hypotheses", preserved["domains"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")

    def test_promotional_reel_is_rejected(self):
        result = evaluate(payload(archive=archive(
            failedExperiments=False,
            setupDetails=False,
            promotionalReelOnly=True,
            domains=["capture"],
        )))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.DOMAIN_OMITTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_missing_domain_is_rejected_even_with_failures_archived(self):
        result = evaluate(payload(archive=archive(domains=["capture", "optics"])))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.DOMAIN_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p155-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(archive=archive(domains=[])))
        with self.assertRaises(ValueError):
            evaluate(payload(archive=archive(failedExperiments="yes")))
