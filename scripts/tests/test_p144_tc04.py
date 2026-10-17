"""Tests for TC-P144-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p144_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p144_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def candidate(**overrides):
    base = {
        "candidate_id": "local-title",
        "match": "misspelling",
        "evidence_status": "unidentified",
    }
    base.update(overrides)
    return base


def payload(**overrides):
    base = {
        "evidenceId": "p144-tc04",
        "repeat": "format",
        "query": "apoclypse",
        "network_used": False,
        "remote_generation_required": False,
        "transparent_matching": True,
        "candidates": [candidate()],
        "recipe": _GATE.preferred_recipe(),
    }
    base.update(overrides)
    return base


class TCP14404(unittest.TestCase):
    def assert_contract(self, result, evidence="p144-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P144-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_local_candidates_keep_evidence_status(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][1]
        self.assertEqual(record["candidates"][0]["evidence_status"], "unidentified")
        self.assertFalse(record["remote_generation_required"])
        self.assertFalse(record["report"]["identification"]["correct"])

    def test_remote_generation_is_rejected(self):
        result = evaluate(payload(remote_generation_required=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.REMOTE, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p144-tc04", result["preservedResults"])

    def test_star_rating_match_is_rejected(self):
        result = evaluate(payload(candidates=[candidate(match="star_rating", evidence_status="reconstructed")]))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.STAR_MATCH, result["rejectedClaims"])
        self.assertFalse(result["preservedResults"][1]["report"]["identification"]["correct"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p144-tc04-monochrome"
        result = evaluate(payload(
            evidenceId=evidence,
            repeat="monochrome",
            candidates=[candidate(match="monochrome", candidate_id="local-mono")],
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(candidates=[candidate(match="popularity")]))
        with self.assertRaises(ValueError):
            evaluate(payload(candidates=[candidate(evidence_status="correct")]))
