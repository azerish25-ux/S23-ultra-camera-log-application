"""Tests for TC-P143-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p143_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p143_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def candidate(candidate_id, match, status="ambiguous", generated=False):
    return {
        "candidateId": candidate_id,
        "match": match,
        "evidenceStatus": status,
        "generated": generated,
    }


def payload(**overrides):
    base = {
        "evidenceId": "p143-tc04",
        "repeat": "format",
        "looks": _GATE.fixture_looks(),
        "dropAmbiguous": False,
        "query": "theatricl 35",
        "remoteGenerationRequired": False,
        "candidates": [
            candidate("local-theatrical", "title token overlap; format 35mm", "documented"),
            candidate("local-alternate", "alternate title; evidence ambiguous", "ambiguous"),
        ],
    }
    base.update(overrides)
    return base


class TCP14304(unittest.TestCase):
    def assert_contract(self, result, evidence="p143-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P143-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 capture was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_local_candidates_are_recorded_without_a_remote_call(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["candidateIds"], ["local-theatrical", "local-alternate"])
        self.assertTrue(record["localLookup"])
        self.assertFalse(record["remoteGenerationRequired"])
        self.assertEqual(len(result["preservedResults"][1]["acceptedKeys"]), 2)

    def test_remote_generation_is_rejected(self):
        result = evaluate(payload(remoteGenerationRequired=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p143-tc04", result["preservedResults"])

    def test_opaque_match_is_rejected(self):
        result = evaluate(payload(candidates=[candidate("local-stock", "  ")]))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.OPAQUE_MATCH, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p143-tc04-scene-family"
        result = evaluate(payload(evidenceId=evidence, repeat="scene-family", query="night interior"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(query=""))
