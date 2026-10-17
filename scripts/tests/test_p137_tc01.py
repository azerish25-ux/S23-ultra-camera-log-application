"""Tests for TC-P137-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p137_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p137_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p137-tc01",
        "repeat": "lens",
        "record": _GATE.fixture_record(),
        "removed": ["lens"],
        "filledLens": None,
    }
    base.update(overrides)
    return base


class TCP13701(unittest.TestCase):
    def assert_contract(self, result, evidence="p137-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P137-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_removed_lens_stays_unknown_while_virtual_lens_is_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["productionLens"]["state"], "unknown")
        self.assertIsNone(detail["productionLens"]["value"])
        self.assertEqual(detail["virtualLens"]["state"], "reconstruction")
        self.assertEqual(detail["stock"]["state"], "fact")
        self.assertEqual(tuple(detail["stateCounts"]), _GATE.STATES)
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")

    def test_removed_stock_becomes_unknown(self):
        result = evaluate(payload(removed=["stock"], repeat="stock"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        detail = result["preservedResults"][1]
        self.assertEqual(detail["stock"]["state"], "unknown")
        self.assertIsNone(detail["stock"]["value"])
        self.assertEqual(detail["virtualLens"]["state"], "reconstruction")
        self.assertEqual(detail["stateCounts"]["unknown"], 3)
        self.assertEqual(detail["stateCounts"]["fact"], 6)

    def test_repeat_fields_can_be_cleared_without_guessing(self):
        for name, repeat in (
            ("camera", "camera"),
            ("process", "process"),
            ("release-version", "release-version"),
        ):
            result = evaluate(payload(removed=[name], repeat=repeat))
            self.assert_contract(result)
            self.assertEqual(result["decision"], "recorded", name)
            self.assertEqual(result["rejectedClaims"], [])

    def test_documented_guess_is_rejected_and_evidence_remains(self):
        filled = _GATE.make_field(
            "lens",
            "documented",
            _GATE.GUESSED_LENS,
            None,
            guessed=True,
            priorState="unknown",
        )
        result = evaluate(payload(filledLens=filled))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.GUESSED_LENS_DOCUMENTED, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        detail = result["preservedResults"][1]
        self.assertEqual(detail["productionLens"]["state"], "unknown")
        self.assertIsNone(detail["productionLens"]["value"])
        self.assertEqual(detail["productionLens"]["submittedValue"], _GATE.GUESSED_LENS)
        self.assertEqual(detail["stateCounts"]["fact"], 7)

    def test_fact_guess_is_rejected(self):
        filled = _GATE.make_field(
            "lens",
            "fact",
            _GATE.GUESSED_LENS,
            "src-guess",
            guessed=True,
            priorState="unknown",
        )
        result = evaluate(payload(filledLens=filled, repeat="lens"))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.GUESSED_LENS_FACT, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["productionLens"]["state"], "unknown")
        self.assertEqual(result["preservedResults"][1]["stateCounts"]["fact"], 7)

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p137-tc01-camera"
        result = evaluate(payload(evidenceId=evidence, repeat="camera", removed=["camera"]))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(removed=["not-a-field"]))
