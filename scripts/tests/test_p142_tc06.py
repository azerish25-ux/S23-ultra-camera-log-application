"""Tests for TC-P142-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p142_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p142_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p142-tc06",
        "repeat": "theatrical",
        "source": _GATE.fixture_source(),
        "reference": _GATE.fixture_reference(),
        "suggestion": _GATE.fixture_suggestion(),
        "editions": _MODULE.clean_editions(),
        "separateTargets": True,
        "uncertaintyExplicit": True,
        "averagedIntoHistoricalFact": False,
        "definitiveLook": None,
    }
    base.update(overrides)
    return base


class TCP14206(unittest.TestCase):
    def assert_contract(self, result, evidence="p142-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P142-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertFalse(result["preservedResults"][1]["newSource"])

    def test_conflicting_editions_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        kept = result["preservedResults"][2]
        self.assertEqual(kept["editionIds"], ["theatrical", "digital", "hdr", "unidentified"])
        self.assertTrue(kept["conflict"])
        self.assertIsNone(kept["definitiveLook"])
        self.assertTrue(_MODULE.editions_conflict(_MODULE.clean_editions()))

    def test_averaging_inconsistent_editions_is_rejected(self):
        result = evaluate(payload(averagedIntoHistoricalFact=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])

    def test_definitive_look_is_rejected(self):
        result = evaluate(payload(definitiveLook="one-true-grade", repeat="hdr"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])

    def test_collapsed_uncertainty_is_rejected(self):
        result = evaluate(payload(
            separateTargets=False,
            uncertaintyExplicit=False,
            repeat="unidentified",
        ))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p142-tc06-digital"
        result = evaluate(payload(evidenceId=evidence, repeat="digital"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(editions=_MODULE.clean_editions()[:1]))
