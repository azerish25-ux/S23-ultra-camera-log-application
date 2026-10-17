"""Tests for TC-P138-01."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p138_tc01",
    Path(__file__).resolve().parents[1] / "gates" / "p138_tc01.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p138-tc01",
        "repeat": "lens",
        "family": _GATE.sample_family(),
        "max_entries": 12,
        "missingField": "lens",
        "guess": None,
        "guessDocumented": False,
        "reconstructionLabelled": True,
    }
    base.update(overrides)
    return base


class TCP13801(unittest.TestCase):
    def assert_contract(self, result, evidence="p138-tc01"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P138-01")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_missing_lens_stays_unknown_on_a_labelled_reconstruction(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        scene = family_entry(result, "scene-12")
        self.assertIsNone(scene["lens"])
        self.assertIsNone(scene["stock"])
        self.assertTrue(scene["reconstruction"])
        self.assertEqual(_MODULE.CASE["name"], "Missing production fact")
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "plausible-guess-marked-documented")

    def test_documented_guess_is_rejected_and_evidence_remains(self):
        family = _GATE.sample_family()
        family[4] = _GATE.make_entry(
            "scene-12",
            lens="Speed Panchro",
            variant="scene",
            scope="scene 12 only",
            reconstruction=False,
            documented=True,
        )
        result = evaluate(payload(guess="Speed Panchro", guessDocumented=True, family=family))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn(_GATE.UNSOURCED_LENS, result["rejectedClaims"])

    def test_camera_guess_marked_documented_is_rejected(self):
        result = evaluate(payload(
            missingField="camera",
            repeat="camera",
            guess="invented body",
            guessDocumented=True,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_stock_repeat_keeps_the_scene_fact_null(self):
        evidence = "p138-tc01-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="stock", missingField="stock"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")
        self.assertIsNone(family_entry(result, "scene-12")["stock"])
        self.assertEqual(family_entry(result, "daylight-5219")["stock"], "5219")

    def test_unlabelled_reconstruction_is_rejected(self):
        result = evaluate(payload(reconstructionLabelled=False))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn("unlabelled-reconstruction", result["rejectedClaims"])

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(missingField="grade"))
        with self.assertRaises(ValueError):
            evaluate(payload(guessDocumented=True))


def family_entry(result, recipe_id):
    for entry in result["preservedResults"][1]["entries"]:
        if entry["recipe_id"] == recipe_id:
            return entry
    raise AssertionError(recipe_id)
