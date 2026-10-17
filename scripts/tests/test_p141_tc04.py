"""Tests for TC-P141-04."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p141_tc04",
    Path(__file__).resolve().parents[1] / "gates" / "p141_tc04.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def candidates():
    return [
        {"candidate_id": "local-title", "match": "edit-distance title", "evidenceStatus": "sourced"},
        {"candidate_id": "alt-title", "match": "alternate title", "evidenceStatus": "partial"},
    ]


def payload(**overrides):
    base = {
        "evidenceId": "p141-tc04",
        "repeat": "format",
        "assets": _GATE.fixture_assets(),
        "query": "apocolypse now",
        "remoteGenerationRequired": False,
        "candidates": candidates(),
    }
    base.update(overrides)
    return base


class TCP14104(unittest.TestCase):
    def assert_contract(self, result, evidence="p141-tc04"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P141-04")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 measurement was not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_local_candidates_are_recorded_without_a_remote_call(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        record = result["preservedResults"][2]
        self.assertEqual(record["query"], "apocolypse now")
        self.assertFalse(record["remoteGenerationRequired"])
        self.assertEqual(record["evidenceStatuses"], ["sourced", "partial"])
        self.assertEqual(_MODULE.NEGATIVE_TOKEN, "remote-generation-required-for-catalogue-lookup")

    def test_remote_generation_is_rejected(self):
        result = evaluate(payload(remoteGenerationRequired=True))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertIn("p141-tc04", result["preservedResults"])

    def test_opaque_or_overclaimed_evidence_is_rejected(self):
        opaque = evaluate(payload(candidates=[{"candidate_id": "x", "match": " ", "evidenceStatus": "unknown"}]))
        self.assertEqual(opaque["decision"], "rejected")
        self.assertIn(_MODULE.OPAQUE_MATCH, opaque["rejectedClaims"])
        over = evaluate(
            payload(candidates=[{"candidate_id": "x", "match": "title", "evidenceStatus": "qualified"}])
        )
        self.assertEqual(over["decision"], "rejected")
        self.assertIn(_MODULE.EVIDENCE_OVERCLAIM, over["rejectedClaims"])
        self.assertNotIn(over["decision"], {"qualified", "allowed"})

    def test_empty_local_result_does_not_require_generation(self):
        result = evaluate(payload(candidates=[], repeat="monochrome"))
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["preservedResults"][2]["candidateIds"], [])

    def test_unlicensed_bytes_are_rejected(self):
        result = evaluate(payload(assets=[_GATE.production_still(bundled=True)], repeat="scene family"))
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_GATE.UNLICENSED_BYTES_BUNDLED, result["rejectedClaims"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p141-tc04-stock"
        result = evaluate(payload(evidenceId=evidence, repeat="scene family", query="vison3"))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate(payload(query=""))
        with self.assertRaises(ValueError):
            evaluate(payload(candidates=[{"candidate_id": "x"}]))
