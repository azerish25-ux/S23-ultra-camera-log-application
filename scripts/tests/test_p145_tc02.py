"""Tests for TC-P145-02."""

from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "p145_tc02",
    Path(__file__).resolve().parents[1] / "gates" / "p145_tc02.py",
)
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)
evaluate = _MODULE.evaluate
_GATE = _MODULE._GATE

KEYS = ("caseId", "decision", "reasons", "rejectedClaims", "preservedResults", "openQuestions")


def payload(**overrides):
    layers = overrides.pop("layers", None)
    if layers is None:
        layers = _GATE.fixture_layers()
        layers["host"] = list(layers["host"]) + [{"id": "timestamp-pairing", "outcome": "failed"}]
    base = {
        "evidenceId": "p145-tc02",
        "repeat": "timestamp-pairing",
        "mutant": "timestamp-pairing",
        "relevantTestId": "timestamp-pairing",
        "lineCoverage": 0.95,
    }
    base.update(_GATE.layer_fields(layers))
    base.update(overrides)
    return base


class TCP14502(unittest.TestCase):
    def assert_contract(self, result, evidence="p145-tc02"):
        self.assertEqual(tuple(result), KEYS)
        self.assertEqual(result["caseId"], "TC-P145-02")
        self.assertNotIn(result["decision"], {"qualified", "allowed"})
        self.assertIn(evidence, result["preservedResults"])
        self.assertIn("physical S23 not run", result["openQuestions"])
        self.assertTrue(result["reasons"])

    def test_case_text_matches_the_spec(self):
        self.assertEqual(_MODULE.CASE["name"], "Critical mutant survives")
        self.assertEqual(
            _MODULE.CASE["negative"],
            "High line coverage without fault detection must not count as adequate protection.",
        )

    def test_killed_mutant_is_recorded(self):
        result = evaluate(payload())
        self.assert_contract(result)
        self.assertEqual(result["decision"], "recorded")
        self.assertEqual(result["rejectedClaims"], [])
        self.assertEqual(result["preservedResults"][2]["killed"], True)
        self.assertEqual(result["preservedResults"][2]["relevantOutcome"], "failed")
        self.assertEqual(result["preservedResults"][1]["totalPassed"], 5)

    def test_high_coverage_without_a_failure_is_rejected(self):
        layers = _GATE.fixture_layers()
        layers["host"] = list(layers["host"]) + [{"id": "timestamp-pairing", "outcome": "passed"}]
        result = evaluate(payload(layers=layers, lineCoverage=0.99))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertIn(_MODULE.CASE["negative"], result["reasons"])
        self.assertEqual(result["preservedResults"][1]["totalPassed"], 6)

    def test_low_coverage_survival_is_still_rejected(self):
        layers = _GATE.fixture_layers()
        layers["host"] = list(layers["host"]) + [{"id": "source-retention", "outcome": "passed"}]
        result = evaluate(payload(
            layers=layers,
            mutant="source-retention",
            relevantTestId="source-retention",
            repeat="source-retention",
            lineCoverage=0.1,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVED, result["rejectedClaims"])
        self.assertNotIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])

    def test_skipped_relevant_test_is_not_a_kill(self):
        layers = _GATE.fixture_layers()
        layers["host"] = list(layers["host"]) + [{"id": "range-signalling", "outcome": "skipped"}]
        result = evaluate(payload(
            layers=layers,
            mutant="range-signalling",
            relevantTestId="range-signalling",
            repeat="range-signalling",
            lineCoverage=0.91,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVED, result["rejectedClaims"])
        self.assertIn(_MODULE.NEGATIVE_TOKEN, result["rejectedClaims"])
        self.assertEqual(result["preservedResults"][2]["relevantOutcome"], "skipped")
        self.assertEqual(result["preservedResults"][1]["layers"]["host"]["skipped"], 1)

    def test_missing_relevant_test_survives(self):
        result = evaluate(payload(
            mutant="checkpoint-identity",
            relevantTestId="checkpoint-identity",
            repeat="checkpoint-identity",
            lineCoverage=0.2,
        ))
        self.assert_contract(result)
        self.assertEqual(result["decision"], "rejected")
        self.assertIn(_MODULE.SURVIVED, result["rejectedClaims"])
        self.assertIsNone(result["preservedResults"][2]["relevantOutcome"])

    def test_second_repeat_preserves_a_different_evidence_id(self):
        evidence = "p145-tc02-checkpoint"
        layers = _GATE.fixture_layers()
        layers["jvm"] = list(layers["jvm"]) + [{"id": "checkpoint-identity", "outcome": "failed"}]
        result = evaluate(payload(
            evidenceId=evidence,
            layers=layers,
            mutant="checkpoint-identity",
            relevantTestId="checkpoint-identity",
            repeat="checkpoint-identity",
        ))
        self.assert_contract(result, evidence)
        self.assertEqual(result["decision"], "recorded")

    def test_invalid_payload_raises(self):
        with self.assertRaises(ValueError):
            evaluate({})
        with self.assertRaises(ValueError):
            evaluate([])
        with self.assertRaises(ValueError):
            evaluate(payload(lineCoverage=1.4))
        with self.assertRaises(ValueError):
            evaluate(payload(mutant="happy-path"))
