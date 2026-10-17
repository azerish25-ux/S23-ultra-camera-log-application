"""Tests for TC-P143-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc06",
        "repeat": "theatrical",
        "looks": _GATE.edition_conflict_looks(),
        "dropAmbiguous": False,
        "averagedIntoHistoricalFact": False,
    }
    base.update(overrides)
    return base


class TCP14306(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_editions_stay_separate(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        distinct = result["preservedResults"][1]["distinctReleaseIds"]["reference-film"]
        self.assertEqual(distinct, ["digital-sdr", "hdr", "theatrical-35mm", "unidentified"])
        self.assertEqual(
            result["preservedResults"][1]["ambiguousReleaseIds"]["reference-film"],
            ["unidentified"],
        )
        contrasts = {
            entry["release_id"]: entry["parameters"]["contrast"]
            for entry in result["preservedResults"][1]["entries"]
        }
        self.assertEqual(contrasts["theatrical-35mm"], 1.5)
        self.assertEqual(contrasts["digital-sdr"], 0.5)
        self.assertEqual(contrasts["hdr"], 1.25)
        self.assertNotEqual(contrasts["theatrical-35mm"], contrasts["digital-sdr"])
        self.assertEqual(_MODULE.CASE["name"], "Reference edition conflict")

    def test_averaging_editions_into_a_fact_is_rejected(self):
        result = evaluate(payload(averagedIntoHistoricalFact=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_GATE.MUTANT, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(len(result["preservedResults"][1]["acceptedKeys"]), 4)

    def test_release_id_all_inside_the_case_is_rejected(self):
        averaged = _GATE.make_look(release_id="all", averaged=True, parameters={"contrast": 1.0})
        result = evaluate(payload(looks=[averaged]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.RELEASE_ID_ALL, result["rejectedClaims"])
        self.assertIn(_GATE.AVERAGED_LOOK, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][1]["acceptedKeys"], [])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc06-hdr"
        result = evaluate(payload(evidenceId=evidence, repeat="hdr"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(averagedIntoHistoricalFact="yes"))
