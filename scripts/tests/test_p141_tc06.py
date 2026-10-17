"""Tests for TC-P141-06."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc06",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc06.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def editions():
    return [
        {"edition_id": "theatrical-cut", "release": "theatrical", "appearance": "print-density"},
        {"edition_id": "digital-master", "release": "digital", "appearance": "video-master"},
        {"edition_id": "hdr-pass", "release": "hdr", "appearance": "hdr-specular"},
        {"edition_id": "unknown-ref", "release": "unidentified", "appearance": "unknown"},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc06",
        "repeat": "theatrical",
        "assets": _GATE.fixture_assets(),
        "editions": editions(),
        "averagedIntoFact": False,
        "separateTargets": True,
        "explicitUncertainty": False,
    }
    base.update(overrides)
    return base


class TCP14106(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc06"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-06")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_separate_targets_are_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertTrue(record["inconsistent"])
        self.assertEqual(record["releases"], ["theatrical", "digital", "hdr", "unidentified"])
        self.assertTrue(record["separateTargets"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "averaged-inconsistent-editions")

    def test_averaging_inconsistent_editions_is_rejected(self):
        result = evaluate(payload(averagedIntoFact=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][2]["releases"][0], "theatrical")

    def test_inventing_one_look_is_rejected(self):
        result = evaluate(payload(separateTargets=False, explicitUncertainty=False, repeat="HDR"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.INVENTED, result["rejectedClaims"])

    def test_explicit_uncertainty_is_recorded(self):
        result = evaluate(
            payload(separateTargets=False, explicitUncertainty=True, repeat="unidentified reference versions")
        )
        self.assertEqual(result["decision"], "recorded")
        self.assertTrue(result["preservedResults"][2]["explicitUncertainty"])

    def test_unlicensed_redistribution_is_rejected(self):
        result = evaluate(payload(assets=[_GATE.production_still(redistribute=True)], repeat="digital"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.REDISTRIBUTE_WITHOUT_LICENCE, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc06-hdr"
        result = evaluate(payload(evidenceId=evidence, repeat="HDR"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            bad = editions()
            bad[0]["release"] = "bluray"
            evaluate(payload(editions=bad))
