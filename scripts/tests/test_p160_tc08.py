"""Tests for TC-P160-08."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p160_tc08",
    Path(__file__).resolve().parents[1] / "gates" / "p160_tc08.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = _GATE.core_payload(repeat="fresh-maintainer reproduction")
    base.update({
        "promotionalReelOnly": False,
        "setupOmitted": False,
        "reproducesCapture": True,
        "reproducesFilmRender": True,
        "reproducesVirtualLens": True,
    })
    base.update(overrides)
    return base


class TCP16008(unittest.TestCase):
    def assert_contract(self, result, evidence="p160-evidence-archive"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P160-08")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_reproducible_closure_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertTrue(result["preservedResults"][1]["includesFailed"])
        self.assertTrue(result["preservedResults"][1]["includesNotRun"])
        self.assertEqual(_MODULE.CASE["name"], "Unreproducible research closure")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "promotional-reel-substitutes-for-archive")

    def test_promotional_reel_cannot_replace_the_archive(self):
        result = evaluate(payload(promotionalReelOnly=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p160-evidence-archive", result["preservedResults"])

    def test_omitted_setup_is_rejected(self):
        result = evaluate(payload(setupOmitted=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SETUP_OMITTED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_incomplete_reproduction_is_rejected(self):
        result = evaluate(payload(reproducesFilmRender=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REPRODUCTION_INCOMPLETE, result["rejectedClaims"])

    def test_favorable_outputs_alone_are_rejected(self):
        result = evaluate(payload(records=_GATE.passes_only_records()))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.PASSES_ONLY, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p160-tc08-optics"
        result = evaluate(payload(evidenceId=evidence, repeat="optics"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(promotionalReelOnly="yes"))
